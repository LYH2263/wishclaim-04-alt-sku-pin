"""端到端：多备选钉选认领。独立 DATA_DIR，直接 init_db 建表。"""
import os
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="wishclaim-test-")

from fastapi.testclient import TestClient
from app import seed
from app.main import app

seed.init_db()
client = TestClient(app)


def make_wish(title="键盘", skus=("A 款", "B 款"), **kw):
    body = {"title": title, "note": ""}
    if skus is not None:
        body["skus"] = [{"title": t, "price": 100 + i} for i, t in enumerate(skus)]
    body.update(kw)
    r = client.post("/api/wishes", json=body)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def get(wid):
    r = client.get(f"/api/wishes/{wid}")
    assert r.status_code == 200
    return r.json()


def test_create_validation():
    assert client.post("/api/wishes", json={"title": "x", "skus": []}).status_code == 400
    too_many = {"title": "x", "skus": [{"title": str(i)} for i in range(6)]}
    assert client.post("/api/wishes", json=too_many).status_code == 400
    blank = {"title": "x", "skus": [{"title": "  "}]}
    assert client.post("/api/wishes", json=blank).status_code == 400


def test_wall_count_and_detail_expand():
    wid = make_wish(skus=("A", "B", "C"))
    wall = client.get("/api/wishes").json()
    row = next(w for w in wall if w["id"] == wid)
    assert row["sku_count"] == 3 and row["selected_sku"] is None
    detail = get(wid)
    assert len(detail["skus"]) == 3
    assert detail["skus"][1]["price"] == 101.0


def test_multi_options_require_explicit_index_and_lock_untouched():
    wid = make_wish()
    r = client.post(f"/api/wishes/{wid}/claim", json={"claimer": "bob"})
    assert r.status_code == 409 and r.json()["detail"] == "sku_required"
    w = get(wid)
    assert w["status"] == "open" and w["claimer"] is None and w["selected_sku"] is None


def test_out_of_range_index_fails_and_lock_untouched():
    wid = make_wish()
    for bad in (5, -1):
        r = client.post(f"/api/wishes/{wid}/claim", json={"claimer": "bob", "sku_index": bad})
        assert r.status_code == 409 and r.json()["detail"] == "sku_index_out_of_range"
    w = get(wid)
    assert w["status"] == "open" and w["claimer"] is None and w["expires_at"] is None


def test_pin_snapshot_consistent_across_three_views():
    wid = make_wish(skus=("A 款", "B 款", "C 款"))
    r = client.post(f"/api/wishes/{wid}/claim", json={"claimer": "bob", "sku_index": 1})
    assert r.status_code == 200
    assert r.json()["selected_sku"] == {"idx": 1, "title": "B 款", "price": 101.0}
    assert get(wid)["selected_sku"]["title"] == "B 款"                      # 详情
    wall = client.get("/api/wishes").json()
    assert next(w for w in wall if w["id"] == wid)["selected_sku"]["idx"] == 1  # 墙摘要
    mine = client.get("/api/mine", params={"claimer": "bob"}).json()
    assert next(w for w in mine if w["id"] == wid)["selected_sku"]["title"] == "B 款"  # 我的认领


def test_publisher_edits_never_rewrite_pin():
    wid = make_wish(skus=("旧A", "旧B"))
    client.post(f"/api/wishes/{wid}/claim", json={"claimer": "bob", "sku_index": 0})
    r = client.put(f"/api/wishes/{wid}/skus",
                   json={"skus": [{"title": "全新备选", "price": 1}]})
    assert r.status_code == 200
    w = get(wid)
    assert [s["title"] for s in w["skus"]] == ["全新备选"]          # 备选已改
    assert w["selected_sku"] == {"idx": 0, "title": "旧A", "price": 100.0}  # 快照不动


def test_put_skus_validates():
    wid = make_wish()
    assert client.put(f"/api/wishes/{wid}/skus", json={"skus": []}).status_code == 400
    assert client.put("/api/wishes/99999/skus",
                      json={"skus": [{"title": "a"}]}).status_code == 404


def test_legacy_wish_defaults_to_single_pin():
    wid = make_wish(title="旧式单愿望", skus=None)
    assert get(wid)["sku_count"] == 1  # 标题合成单条
    r = client.post(f"/api/wishes/{wid}/claim", json={"claimer": "bob"})
    assert r.status_code == 200
    assert r.json()["selected_sku"] == {"idx": 0, "title": "旧式单愿望", "price": None}


def test_zero_option_wish_claim_fails_lock_untouched():
    wid = make_wish(title="", skus=None)  # 空标题遗留 → 零备选
    assert get(wid)["sku_count"] == 0
    r = client.post(f"/api/wishes/{wid}/claim", json={"claimer": "bob"})
    assert r.status_code == 409 and r.json()["detail"] == "no_sku_options"
    w = get(wid)
    assert w["status"] == "open" and w["claimer"] is None


def test_release_clears_pin():
    wid = make_wish()
    client.post(f"/api/wishes/{wid}/claim", json={"claimer": "bob", "sku_index": 1})
    client.post(f"/api/wishes/{wid}/release")
    w = get(wid)
    assert w["status"] == "released" and w["selected_sku"] is None
