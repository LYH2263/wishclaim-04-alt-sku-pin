from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app import seed
from app.db import connect
from app.engines.claim_lock import claim_allowed, lock_payload, release_if_expired
from app.engines.sku_pin import resolve_pin
from app.modules.sku_options import SkuError, decode_skus, normalize_skus, encode_skus, encode_snapshot
from app.modules.sku_view import wall_card, detail_view, claim_view

app = FastAPI(title="Wishclaim", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def _startup(): seed.init_db()

def now(): return datetime.now(timezone.utc)

def ttl():
    c = connect(); row = c.execute("SELECT value FROM settings WHERE key='ttl_seconds'").fetchone(); c.close()
    return int(row["value"] if row else 86400)

def sweep(c):
    for r in c.execute("SELECT * FROM wishes WHERE status='claimed'"):
        rel = release_if_expired(r["status"], r["expires_at"], now())
        if rel:
            c.execute("UPDATE wishes SET status=?, claimer=?, claimed_at=?, expires_at=?, selected_sku=? WHERE id=?",
                      (rel["status"], None, None, None, None, r["id"]))

@app.get("/api/health")
def health(): return {"ok": True, "project": "wishclaim"}

@app.get("/api/wishes")
def list_wishes():
    c = connect(); sweep(c); c.commit()
    rows = [wall_card(dict(r)) for r in c.execute("SELECT * FROM wishes ORDER BY id DESC")]; c.close(); return rows

@app.get("/api/wishes/{wid}")
def get_wish(wid: int):
    c = connect(); sweep(c); c.commit()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone(); c.close()
    if not r: raise HTTPException(404, "not found")
    return detail_view(dict(r))

class SkuIn(BaseModel):
    title: str
    estimated_price: str = ""

class WishIn(BaseModel):
    title: str
    note: str = ""
    skus: list[SkuIn]

@app.post("/api/wishes")
def create_wish(body: WishIn):
    # 发愿望必须挂 2~5 条备选（标题+估价）
    try:
        skus = normalize_skus([s.model_dump() for s in body.skus], min_count=2)
    except SkuError as e:
        raise HTTPException(400, e.reason)
    c = connect()
    cur = c.execute("INSERT INTO wishes(title,note,status,data_quality,skus,selected_sku) VALUES (?,?,?,?,?,?)",
                    (body.title, body.note, "open", "clean", encode_skus(skus), None))
    c.commit(); wid = cur.lastrowid; c.close(); return {"id": wid}

class ClaimIn(BaseModel):
    claimer: str
    sku_index: Optional[int] = None

@app.post("/api/wishes/{wid}/claim")
def claim(wid: int, body: ClaimIn):
    c = connect(); sweep(c); c.commit()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    allowed = claim_allowed(r["status"], r["claimer"], now(), r["expires_at"])
    if not allowed["ok"]:
        c.close(); raise HTTPException(409, allowed["reason"])
    # 钉选裁决：零备选 / 越界 / 多条未显式选择 → 直接失败，不写任何字段（锁不变）
    pin = resolve_pin(decode_skus(r["skus"]), body.sku_index)
    if not pin["ok"]:
        c.close(); raise HTTPException(400, pin["reason"])
    p = lock_payload(body.claimer, now(), ttl())
    # 互斥锁与钉选快照在同一条 UPDATE 落库，同生共死
    c.execute("UPDATE wishes SET status=?, claimer=?, claimed_at=?, expires_at=?, selected_sku=? WHERE id=?",
              (p["status"], p["claimer"], p["claimed_at"], p["expires_at"],
               encode_snapshot(pin["snapshot"]), wid))
    c.commit(); c.close(); return {**p, "selected_sku": pin["snapshot"]}

class SkusPatch(BaseModel):
    skus: list[SkuIn]

@app.get("/api/wishes/{wid}/skus")
def get_skus(wid: int):
    """发布者管理备选用：返回原始备选列表（独立于墙/详情/我的认领只读投影）。"""
    c = connect()
    r = c.execute("SELECT status, skus FROM wishes WHERE id=?", (wid,)).fetchone(); c.close()
    if not r: raise HTTPException(404, "not found")
    return {"status": r["status"], "skus": decode_skus(r["skus"])}

@app.patch("/api/wishes/{wid}/skus")
def update_skus(wid: int, body: SkusPatch):
    """发布者增删备选（1~5 条），认领前后均可；只改 skus 列，永不触碰 selected_sku。

    钉选快照自含标题/估价/索引，认领后增删备选不改写快照，墙/详情/我的认领
    三路继续展示认领那一刻钉住的内容；释放后再按新的备选列表重新认领。
    """
    c = connect()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    if r["status"] == "fulfilled":
        c.close(); raise HTTPException(409, "already_fulfilled")
    try:
        skus = normalize_skus([s.model_dump() for s in body.skus], min_count=1)
    except SkuError as e:
        c.close(); raise HTTPException(400, e.reason)
    c.execute("UPDATE wishes SET skus=? WHERE id=?", (encode_skus(skus), wid))
    c.commit(); c.close(); return {"ok": True, "sku_count": len(skus)}

@app.post("/api/wishes/{wid}/release")
def release(wid: int):
    c = connect()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    if r["status"] != "claimed":
        c.close(); raise HTTPException(400, "not_claimed")
    c.execute("UPDATE wishes SET status='released', claimer=NULL, claimed_at=NULL, expires_at=NULL, "
              "selected_sku=NULL WHERE id=?", (wid,))
    c.commit(); c.close(); return {"ok": True, "status": "released"}

@app.post("/api/wishes/{wid}/fulfill")
def fulfill(wid: int):
    c = connect()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    if r["status"] != "claimed":
        c.close(); raise HTTPException(400, "need_claim")
    c.execute("UPDATE wishes SET status='fulfilled' WHERE id=?", (wid,))
    c.commit(); c.close(); return {"ok": True, "status": "fulfilled"}

@app.get("/api/mine")
def mine(claimer: str):
    c = connect(); sweep(c); c.commit()
    rows = [claim_view(dict(r)) for r in c.execute("SELECT * FROM wishes WHERE claimer=?", (claimer,))]; c.close(); return rows

@app.get("/api/done")
def done():
    c = connect()
    rows = [claim_view(dict(r)) for r in c.execute("SELECT * FROM wishes WHERE status='fulfilled'")]; c.close(); return rows

@app.get("/api/settings")
def settings():
    c = connect(); rows = {r["key"]: r["value"] for r in c.execute("SELECT * FROM settings")}; c.close(); return rows

@app.get("/api/rules")
def rules():
    return {
        "mutex": "同一愿望同时只能被一人认领",
        "ttl": "认领超时未核销则自动释放",
        "fulfill": "核销后状态变为 fulfilled",
        "sku": "发布须挂 2~5 条备选，认领时必须显式钉选其中一条",
        "pin": "认领后三路只展示钉选快照，发布者增删备选不改写钉选",
    }
