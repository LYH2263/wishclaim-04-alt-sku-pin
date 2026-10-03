import pytest
from app.modules.sku_options import (
    normalize_skus, encode_skus, decode_skus, snapshot, encode_snapshot, decode_snapshot, SkuError,
)

def _sku(t, p=""):
    return {"title": t, "estimated_price": p}

def test_accepts_2_to_5_on_create():
    assert len(normalize_skus([_sku("a"), _sku("b")], min_count=2)) == 2
    assert len(normalize_skus([_sku(f"s{i}") for i in range(5)], min_count=2)) == 5

@pytest.mark.parametrize("n", [0, 1, 6])
def test_rejects_out_of_range_on_create(n):
    with pytest.raises(SkuError) as e:
        normalize_skus([_sku(f"s{i}") for i in range(n)], min_count=2)
    assert e.value.reason == "sku_count"

def test_edit_allows_single():
    assert len(normalize_skus([_sku("only")], min_count=1)) == 1

def test_edit_rejects_empty_and_over_five():
    with pytest.raises(SkuError) as e0:
        normalize_skus([], min_count=1)
    assert e0.value.reason == "sku_count"
    with pytest.raises(SkuError) as e6:
        normalize_skus([_sku(f"s{i}") for i in range(6)], min_count=1)
    assert e6.value.reason == "sku_count"

def test_title_required_and_trimmed():
    with pytest.raises(SkuError) as e:
        normalize_skus([_sku("  "), _sku("b")], min_count=2)
    assert e.value.reason == "sku_title_missing"
    out = normalize_skus([_sku(" a "), _sku("b")], min_count=2)
    assert out[0]["title"] == "a"

def test_shape_errors():
    with pytest.raises(SkuError) as e:
        normalize_skus("nope", min_count=2)
    assert e.value.reason == "sku_shape"
    with pytest.raises(SkuError) as e:
        normalize_skus(["x", _sku("b")], min_count=2)
    assert e.value.reason == "sku_shape"

def test_price_coerced_and_optional():
    out = normalize_skus([{"title": "a", "estimated_price": 380}, {"title": "b"}], min_count=2)
    assert out[0]["estimated_price"] == "380"
    assert out[1]["estimated_price"] == ""

def test_codec_roundtrip():
    skus = [_sku("红轴键盘", "380"), _sku("茶轴", "420")]
    assert decode_skus(encode_skus(skus)) == skus

def test_decode_garbage_is_empty():
    assert decode_skus(None) == []
    assert decode_skus("not-json") == []
    assert decode_skus('{"a":1}') == []

def test_snapshot_bounds():
    skus = [_sku("a", "1"), _sku("b", "2")]
    assert snapshot(skus, 0) == {"title": "a", "estimated_price": "1", "sku_index": 0}
    assert snapshot(skus, 2) is None
    assert snapshot(skus, -1) is None
    assert snapshot([], 0) is None

def test_snapshot_codec():
    s = snapshot([_sku("a", "9")], 0)
    assert decode_snapshot(encode_snapshot(s)) == s
    assert decode_snapshot(None) is None
    assert decode_snapshot("xx") is None
