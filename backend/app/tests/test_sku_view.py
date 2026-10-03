from app.modules.sku_view import wall_card, detail_view, claim_view
from app.modules.sku_options import encode_skus, encode_snapshot

SKUS = [
    {"title": "红轴", "estimated_price": "380"},
    {"title": "茶轴", "estimated_price": "420"},
    {"title": "银轴", "estimated_price": "500"},
]
SNAP2 = {"title": "银轴", "estimated_price": "500", "sku_index": 2}

def _row(status, *, pinned=False):
    return {
        "id": 1, "title": "键盘", "note": "", "status": status,
        "claimer": "alice" if pinned else None, "claimed_at": None, "expires_at": None,
        "data_quality": "clean", "skus": encode_skus(SKUS),
        "selected_sku": encode_snapshot(SNAP2) if pinned else None,
    }

def test_wall_open_shows_count_only():
    c = wall_card(_row("open"))
    assert c["sku_count"] == 3
    assert "selected_sku" not in c
    assert "skus" not in c

def test_detail_open_lists_all():
    d = detail_view(_row("open"))
    assert d["skus"] == SKUS and d["sku_count"] == 3
    assert "selected_sku" not in d

def test_three_views_pin_to_same_snapshot_when_claimed():
    for status in ("claimed", "fulfilled"):
        row = _row(status, pinned=True)
        wc, dv, mv = wall_card(row), detail_view(row), claim_view(row)
        assert wc["selected_sku"] == SNAP2
        assert dv["selected_sku"] == SNAP2
        assert mv["selected_sku"] == SNAP2
        # 认领后墙卡与详情均不列出其余备选（不灰显、不展开）
        assert "skus" not in dv
        assert "skus" not in wc and "sku_count" not in wc

def test_claimed_without_snapshot_shows_none_not_the_list():
    row = _row("claimed", pinned=False)
    assert wall_card(row)["selected_sku"] is None
    assert detail_view(row)["selected_sku"] is None
    assert "skus" not in detail_view(row)

def test_released_goes_back_to_count_view():
    row = _row("released", pinned=False)
    assert wall_card(row)["sku_count"] == 3
    assert detail_view(row)["skus"] == SKUS
