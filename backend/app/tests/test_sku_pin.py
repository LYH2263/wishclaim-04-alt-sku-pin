from app.engines.sku_pin import resolve_pin

SKUS = [
    {"title": "红轴", "estimated_price": "380"},
    {"title": "茶轴", "estimated_price": "420"},
    {"title": "银轴", "estimated_price": "500"},
]

def test_multi_requires_explicit_index():
    r = resolve_pin(SKUS, None)
    assert r == {"ok": False, "reason": "sku_selection_required"}

def test_explicit_pin_takes_snapshot():
    r = resolve_pin(SKUS, 1)
    assert r["ok"] is True
    assert r["snapshot"] == {"title": "茶轴", "estimated_price": "420", "sku_index": 1}

def test_out_of_range_rejected():
    assert resolve_pin(SKUS, 3)["reason"] == "sku_index_bad"
    assert resolve_pin(SKUS, -1)["reason"] == "sku_index_bad"
    assert resolve_pin(SKUS, "1")["reason"] == "sku_index_bad"
    assert resolve_pin(SKUS, True)["reason"] == "sku_index_bad"

def test_zero_skus_rejected():
    assert resolve_pin([], None)["reason"] == "sku_none"
    assert resolve_pin([], 0)["reason"] == "sku_none"

def test_single_sku_defaults_to_zero():
    """仅一条备选时默认选中，兼容改造前单愿望认领。"""
    one = [{"title": "围巾", "estimated_price": "260"}]
    r = resolve_pin(one, None)
    assert r["ok"] is True
    assert r["snapshot"] == {"title": "围巾", "estimated_price": "260", "sku_index": 0}
    # 显式给 0 同样通过
    assert resolve_pin(one, 0)["snapshot"]["sku_index"] == 0
    assert resolve_pin(one, 1)["reason"] == "sku_index_bad"
