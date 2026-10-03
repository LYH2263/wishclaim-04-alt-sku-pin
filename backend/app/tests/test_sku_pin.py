from datetime import datetime, timedelta, timezone
from app.engines.claim_lock import lock_payload, release_if_expired, resolve_pin

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
OPTS = [
    {"idx": 0, "title": "A 款", "price": 100.0},
    {"idx": 1, "title": "B 款", "price": None},
]


def test_zero_options_fails():
    assert resolve_pin([], None) == {"ok": False, "reason": "no_sku_options"}
    assert resolve_pin([], 0) == {"ok": False, "reason": "no_sku_options"}


def test_single_option_defaults_to_zero():
    r = resolve_pin([{"idx": 0, "title": "唯一", "price": 9.0}], None)
    assert r["ok"] is True
    assert r["selected"] == {"idx": 0, "title": "唯一", "price": 9.0}


def test_multi_options_require_explicit_index():
    assert resolve_pin(OPTS, None) == {"ok": False, "reason": "sku_required"}


def test_explicit_index_pins_snapshot():
    r = resolve_pin(OPTS, 1)
    assert r["ok"] is True
    assert r["selected"] == {"idx": 1, "title": "B 款", "price": None}


def test_out_of_range_index_fails():
    for bad in (2, -1, 99):
        assert resolve_pin(OPTS, bad) == {"ok": False, "reason": "sku_index_out_of_range"}


def test_non_int_index_fails():
    for bad in ("0", 1.5, True, {"i": 0}):
        assert resolve_pin(OPTS, bad)["reason"] == "sku_index_out_of_range"


def test_lock_payload_carries_pin_snapshot():
    sel = resolve_pin(OPTS, 0)["selected"]
    p = lock_payload("bob", NOW, 3600, sel)
    assert p["selected_sku"] == {"idx": 0, "title": "A 款", "price": 100.0}
    assert p["status"] == "claimed"


def test_lock_payload_without_pin_stays_compatible():
    p = lock_payload("bob", NOW, 3600)
    assert p["selected_sku"] is None


def test_release_clears_pin():
    rel = release_if_expired("claimed", (NOW - timedelta(seconds=1)).isoformat(), NOW)
    assert rel["status"] == "open" and rel["selected_sku"] is None
