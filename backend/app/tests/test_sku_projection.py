import json
import sqlite3
import pytest
from app.modules.sku_projection import (
    attach_detail, attach_summary, load_options, options_for_wish,
    parse_selected, replace_options,
)


@pytest.fixture
def c():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE wish_skus(id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " wish_id INTEGER, idx INTEGER, title TEXT, price REAL)"
    )
    yield conn
    conn.close()


def wish(wid, title="键盘", selected=None):
    return {"id": wid, "title": title, "selected_sku": selected}


def test_replace_and_load_roundtrip(c):
    replace_options(c, 1, [{"idx": 0, "title": "A", "price": 1.5},
                           {"idx": 1, "title": "B", "price": None}])
    assert load_options(c, 1) == [
        {"idx": 0, "title": "A", "price": 1.5},
        {"idx": 1, "title": "B", "price": None},
    ]


def test_legacy_fallback_synthesizes_single_option(c):
    opts = options_for_wish(c, wish(9, "旧愿望"))
    assert len(opts) == 1 and opts[0]["title"] == "旧愿望" and opts[0]["legacy"] is True


def test_empty_title_yields_zero_options(c):
    assert options_for_wish(c, wish(9, "")) == []
    assert options_for_wish(c, wish(9, "   ")) == []


def test_db_rows_win_over_fallback(c):
    replace_options(c, 9, [{"idx": 0, "title": "新备选", "price": 3.0}])
    opts = options_for_wish(c, wish(9, "旧标题"))
    assert opts == [{"idx": 0, "title": "新备选", "price": 3.0}]


def test_parse_selected_tolerates_dirty_data():
    assert parse_selected(wish(1, selected=None)) is None
    assert parse_selected(wish(1, selected="not-json")) is None
    sel = {"idx": 1, "title": "B", "price": 2.0}
    assert parse_selected(wish(1, selected=json.dumps(sel))) == sel


def test_summary_view_carries_count_and_pin(c):
    v = attach_summary({}, wish(1, selected=json.dumps({"idx": 0, "title": "A", "price": 1})),
                       [{"idx": 0}, {"idx": 1}])
    assert v["sku_count"] == 2 and v["selected_sku"]["title"] == "A"


def test_detail_view_carries_all_options(c):
    opts = [{"idx": 0, "title": "A"}, {"idx": 1, "title": "B"}]
    v = attach_detail({}, wish(1), opts)
    assert v["skus"] == opts and v["selected_sku"] is None


def test_pin_snapshot_immune_to_option_edits(c):
    """认领后增删备选（replace_options）不改写 wishes 行上的已钉快照。"""
    pinned = {"idx": 1, "title": "B", "price": 2.0}
    row = wish(1, selected=json.dumps(pinned))
    replace_options(c, 1, [{"idx": 0, "title": "A", "price": 1.0},
                           {"idx": 1, "title": "B", "price": 2.0}])
    replace_options(c, 1, [{"idx": 0, "title": "全新备选", "price": 9.0}])
    v = attach_summary({}, row, options_for_wish(c, row))
    assert v["selected_sku"] == pinned
    assert v["sku_count"] == 1
