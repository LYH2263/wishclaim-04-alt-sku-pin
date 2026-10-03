import json
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app import seed
from app.db import connect
from app.engines.claim_lock import claim_allowed, lock_payload, release_if_expired, resolve_pin
from app.modules.sku_options import validate_options
from app.modules.sku_projection import (
    attach_detail, attach_summary, options_for_wish, replace_options,
)

app = FastAPI(title="Wishclaim", version="0.2.0")
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
    rows = [attach_summary(dict(r), r, options_for_wish(c, r))
            for r in c.execute("SELECT * FROM wishes ORDER BY id DESC")]
    c.close(); return rows

@app.get("/api/wishes/{wid}")
def get_wish(wid: int):
    c = connect(); sweep(c); c.commit()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    view = attach_detail(dict(r), r, options_for_wish(c, r)); c.close(); return view

class WishIn(BaseModel):
    title: str
    note: str = ""
    skus: list | None = None  # 缺省 = 遗留单愿望（由标题合成单条备选）

@app.post("/api/wishes")
def create_wish(body: WishIn):
    options = []
    if body.skus is not None:
        v = validate_options(body.skus)
        if not v["ok"]: raise HTTPException(400, v["reason"])
        options = v["options"]
    c = connect()
    cur = c.execute("INSERT INTO wishes(title,note,status,data_quality) VALUES (?,?,?,?)",
                    (body.title, body.note, "open", "clean"))
    wid = cur.lastrowid
    if options: replace_options(c, wid, options)
    c.commit(); c.close(); return {"id": wid}

class SkusIn(BaseModel):
    skus: list

@app.put("/api/wishes/{wid}/skus")
def put_skus(wid: int, body: SkusIn):
    """发布者增删备选。已钉 selected_sku 快照一律不改写。"""
    c = connect()
    r = c.execute("SELECT id FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    v = validate_options(body.skus)
    if not v["ok"]: c.close(); raise HTTPException(400, v["reason"])
    replace_options(c, wid, v["options"])
    c.commit(); c.close()
    return {"ok": True, "skus": v["options"]}

class ClaimIn(BaseModel):
    claimer: str
    sku_index: int | None = None

@app.post("/api/wishes/{wid}/claim")
def claim(wid: int, body: ClaimIn):
    c = connect(); sweep(c); c.commit()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    allowed = claim_allowed(r["status"], r["claimer"], now(), r["expires_at"])
    if not allowed["ok"]:
        c.close(); raise HTTPException(409, allowed["reason"])
    # 钉选解析失败（零备选/越界/多选未指定）→ 直接 409，锁保持不变
    pin = resolve_pin(options_for_wish(c, r), body.sku_index)
    if not pin["ok"]:
        c.close(); raise HTTPException(409, pin["reason"])
    p = lock_payload(body.claimer, now(), ttl(), pin["selected"])
    c.execute("UPDATE wishes SET status=?, claimer=?, claimed_at=?, expires_at=?, selected_sku=? WHERE id=?",
              (p["status"], p["claimer"], p["claimed_at"], p["expires_at"],
               json.dumps(p["selected_sku"], ensure_ascii=False), wid))
    c.commit(); c.close(); return p

@app.post("/api/wishes/{wid}/release")
def release(wid: int):
    c = connect()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    if r["status"] != "claimed":
        c.close(); raise HTTPException(400, "not_claimed")
    c.execute("UPDATE wishes SET status='released', claimer=NULL, claimed_at=NULL, expires_at=NULL,"
              " selected_sku=NULL WHERE id=?", (wid,))
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
    rows = [attach_summary(dict(r), r, options_for_wish(c, r))
            for r in c.execute("SELECT * FROM wishes WHERE claimer=?", (claimer,))]
    c.close(); return rows

@app.get("/api/done")
def done():
    c = connect()
    rows = [attach_summary(dict(r), r, options_for_wish(c, r))
            for r in c.execute("SELECT * FROM wishes WHERE status='fulfilled'")]
    c.close(); return rows

@app.get("/api/settings")
def settings():
    c = connect(); rows = {r["key"]: r["value"] for r in c.execute("SELECT * FROM settings")}; c.close(); return rows

@app.get("/api/rules")
def rules():
    return {
        "mutex": "同一愿望同时只能被一人认领",
        "ttl": "认领超时未核销则自动释放",
        "fulfill": "核销后状态变为 fulfilled",
        "sku": "认领需显式钉选一条备选；快照不随发布者后续增删改变",
    }
