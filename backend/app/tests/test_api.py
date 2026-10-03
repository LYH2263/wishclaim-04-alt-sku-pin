import json
import importlib

SKUS3 = [
    {"title": "红轴键盘", "estimated_price": "380"},
    {"title": "茶轴键盘", "estimated_price": "420"},
    {"title": "银轴键盘", "estimated_price": "500"},
]

def _create(client, skus, title="键盘", note=""):
    r = client.post("/api/wishes", json={"title": title, "note": note, "skus": skus})
    assert r.status_code == 200, r.text
    return r.json()["id"]

def test_create_requires_2_to_5(client):
    r = client.post("/api/wishes", json={"title": "x", "skus": [SKUS3[0]]})
    assert r.status_code == 400 and r.json()["detail"] == "sku_count"
    r = client.post("/api/wishes", json={"title": "x", "skus": [{"title": f"s{i}"} for i in range(6)]})
    assert r.status_code == 400 and r.json()["detail"] == "sku_count"
    r = client.post("/api/wishes", json={"title": "x", "skus": [{"title": ""}, SKUS3[1]]})
    assert r.status_code == 400 and r.json()["detail"] == "sku_title_missing"

def test_wall_count_and_detail_list_before_claim(client):
    wid = _create(client, SKUS3)
    card = next(w for w in client.get("/api/wishes").json() if w["id"] == wid)
    assert card["sku_count"] == 3 and "selected_sku" not in card and "skus" not in card
    d = client.get(f"/api/wishes/{wid}").json()
    assert d["skus"] == SKUS3 and d["sku_count"] == 3

def test_claim_multi_requires_explicit_selection_and_lock_untouched(client):
    wid = _create(client, SKUS3)
    r = client.post(f"/api/wishes/{wid}/claim", json={"claimer": "alice"})
    assert r.status_code == 400 and r.json()["detail"] == "sku_selection_required"
    d = client.get(f"/api/wishes/{wid}").json()
    assert d["status"] == "open" and d["claimer"] is None and d["skus"] == SKUS3

def test_claim_bad_index_fails_without_touching_lock(client):
    wid = _create(client, SKUS3)
    for bad in (3, -1):
        r = client.post(f"/api/wishes/{wid}/claim", json={"claimer": "alice", "sku_index": bad})
        assert r.status_code == 400 and r.json()["detail"] == "sku_index_bad"
    d = client.get(f"/api/wishes/{wid}").json()
    assert d["status"] == "open" and d["claimer"] is None and d["expires_at"] is None

def test_zero_skus_claim_fails_and_lock_untouched(client):
    from app.db import connect
    c = connect()
    cur = c.execute("INSERT INTO wishes(title,note,status,data_quality,skus,selected_sku) VALUES (?,?,?,?,?,?)",
                    ("空备选", "", "open", "dirty", "[]", None))
    c.commit(); wid = cur.lastrowid; c.close()
    r = client.post(f"/api/wishes/{wid}/claim", json={"claimer": "alice", "sku_index": 0})
    assert r.status_code == 400 and r.json()["detail"] == "sku_none"
    d = client.get(f"/api/wishes/{wid}").json()
    assert d["status"] == "open" and d["claimer"] is None

def test_claim_writes_snapshot_and_three_views_share_one_pin(client):
    wid = _create(client, SKUS3)
    r = client.post(f"/api/wishes/{wid}/claim", json={"claimer": "alice", "sku_index": 2})
    assert r.status_code == 200
    assert r.json()["selected_sku"] == {"title": "银轴键盘", "estimated_price": "500", "sku_index": 2}

    card = next(w for w in client.get("/api/wishes").json() if w["id"] == wid)
    detail = client.get(f"/api/wishes/{wid}").json()
    mine = next(w for w in client.get("/api/mine?claimer=alice").json() if w["id"] == wid)
    # 三路同钉：只展示钉选一条，均不返回其余备选
    for v in (card, detail, mine):
        assert v["selected_sku"] == {"title": "银轴键盘", "estimated_price": "500", "sku_index": 2}
        assert "skus" not in v and "sku_count" not in v

def test_publisher_edit_after_claim_never_rewrites_pin(client):
    wid = _create(client, SKUS3)
    client.post(f"/api/wishes/{wid}/claim", json={"claimer": "alice", "sku_index": 2})
    # 认领后增删备选：删掉被钉的标题、改掉估价、缩成两条
    new_skus = [{"title": "全新红轴", "estimated_price": "999"}, {"title": "全新茶轴", "estimated_price": "1"}]
    r = client.patch(f"/api/wishes/{wid}/skus", json={"skus": new_skus})
    assert r.status_code == 200
    pin = {"title": "银轴键盘", "estimated_price": "500", "sku_index": 2}
    detail = client.get(f"/api/wishes/{wid}").json()
    card = next(w for w in client.get("/api/wishes").json() if w["id"] == wid)
    mine = next(w for w in client.get("/api/mine?claimer=alice").json() if w["id"] == wid)
    for v in (detail, card, mine):
        assert v["selected_sku"] == pin and "skus" not in v

def test_fulfilled_pin_frozen_and_done_shows_pin(client):
    wid = _create(client, SKUS3)
    client.post(f"/api/wishes/{wid}/claim", json={"claimer": "alice", "sku_index": 0})
    client.post(f"/api/wishes/{wid}/fulfill")
    assert client.patch(f"/api/wishes/{wid}/skus", json={"skus": SKUS3[:2]}).status_code == 409
    done = next(w for w in client.get("/api/done").json() if w["id"] == wid)
    assert done["selected_sku"]["title"] == "红轴键盘"

def test_release_clears_pin_and_new_list_becomes_choosable(client):
    wid = _create(client, SKUS3)
    client.post(f"/api/wishes/{wid}/claim", json={"claimer": "alice", "sku_index": 2})
    new_skus = [{"title": "新唯一款", "estimated_price": "88"}]
    client.patch(f"/api/wishes/{wid}/skus", json={"skus": new_skus})
    assert client.post(f"/api/wishes/{wid}/release").status_code == 200
    d = client.get(f"/api/wishes/{wid}").json()
    assert d["status"] == "released" and "selected_sku" not in d and d["skus"] == new_skus
    # 释放后单备选可默认选中重新认领
    r = client.post(f"/api/wishes/{wid}/claim", json={"claimer": "bob"})
    assert r.status_code == 200 and r.json()["selected_sku"]["title"] == "新唯一款"

def test_legacy_single_sku_defaults_on_claim(client):
    """种子里的旧单愿望回填为一条备选，无索引认领兼容成功。"""
    rows = client.get("/api/wishes").json()
    wid = next(w["id"] for w in rows if w["title"] == "围巾" and w["sku_count"] == 1)
    r = client.post(f"/api/wishes/{wid}/claim", json={"claimer": "carol"})
    assert r.status_code == 200
    assert r.json()["selected_sku"]["sku_index"] == 0

def test_mutex_still_blocks_second_claimer(client):
    wid = _create(client, SKUS3)
    client.post(f"/api/wishes/{wid}/claim", json={"claimer": "alice", "sku_index": 0})
    r = client.post(f"/api/wishes/{wid}/claim", json={"claimer": "bob", "sku_index": 1})
    assert r.status_code == 409 and r.json()["detail"] == "locked"
    # 败者的钉选不得覆盖先到者
    d = client.get(f"/api/wishes/{wid}").json()
    assert d["claimer"] == "alice" and d["selected_sku"]["sku_index"] == 0

def test_legacy_schema_migration_backfills_single_sku(tmp_path, monkeypatch):
    import sqlite3, os
    d = tmp_path / "legacy"; d.mkdir()
    dbfile = d / "wishclaim.db"
    raw = sqlite3.connect(dbfile)
    raw.execute("CREATE TABLE wishes(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, note TEXT, status TEXT, "
                "claimer TEXT, claimed_at TEXT, expires_at TEXT, data_quality TEXT)")
    raw.execute("INSERT INTO wishes(title,note,status,data_quality) VALUES (?,?,?,?)",
                ("旧愿望's", "", "open", "clean"))
    raw.commit(); raw.close()
    monkeypatch.setenv("DATA_DIR", str(d))
    import app.seed
    importlib.reload(app.seed)
    app.seed.init_db()
    import sqlite3 as s2
    c = s2.connect(dbfile); c.row_factory = s2.Row
    row = c.execute("SELECT skus, selected_sku FROM wishes WHERE title=?", ("旧愿望's",)).fetchone()
    skus = json.loads(row["skus"])
    assert row["selected_sku"] is None
    assert skus == [{"title": "旧愿望's", "estimated_price": ""}]
    c.close()
