from app.modules.sku_options import MAX_OPTIONS, validate_options


def opt(title="机械键盘", price=100):
    return {"title": title, "price": price}


def test_valid_range_1_to_5():
    for n in (1, 2, MAX_OPTIONS):
        r = validate_options([opt() for _ in range(n)])
        assert r["ok"] is True
        assert [o["idx"] for o in r["options"]] == list(range(n))


def test_zero_options_rejected():
    assert validate_options([]) == {"ok": False, "reason": "sku_count_out_of_range"}


def test_six_options_rejected():
    r = validate_options([opt() for _ in range(MAX_OPTIONS + 1)])
    assert r["ok"] is False and r["reason"] == "sku_count_out_of_range"


def test_not_a_list_rejected():
    assert validate_options("x")["reason"] == "sku_options_not_a_list"
    assert validate_options(None)["reason"] == "sku_options_not_a_list"


def test_blank_title_rejected():
    assert validate_options([opt("")])["reason"] == "sku_title_required"
    assert validate_options([opt("   ")])["reason"] == "sku_title_required"
    assert validate_options([{"price": 1}])["reason"] == "sku_title_required"


def test_overlong_title_rejected():
    assert validate_options([opt("长" * 81)])["reason"] == "sku_title_too_long"


def test_negative_and_garbage_price_rejected():
    assert validate_options([opt(price=-1)])["reason"] == "sku_price_invalid"
    assert validate_options([opt(price="abc")])["reason"] == "sku_price_invalid"
    assert validate_options([opt(price=True)])["reason"] == "sku_price_invalid"
    assert validate_options([opt(price=float("inf"))])["reason"] == "sku_price_invalid"


def test_normalization_strips_and_defaults():
    r = validate_options([{"title": "  围巾  "}, {"title": "键盘", "price": 0}])
    assert r["ok"] is True
    assert r["options"][0] == {"idx": 0, "title": "围巾", "price": None}
    assert r["options"][1]["price"] == 0.0
