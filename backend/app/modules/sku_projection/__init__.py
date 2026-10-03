"""投影：wishes 行 + wish_skus 行 → 墙摘要 / 详情 / 我的认领 三路视图。

拍板（与详情一致）：认领后三路均「只展示钉选一条」——selected_sku
快照一旦写入，各视图只突出快照；其余备选不再在卡片/详情中列出。

兼容：没有 SKU 行的遗留愿望，由标题合成单条备选（可缺省认领）；
标题为空的脏数据愿望合成不出备选 → 零备选，认领失败且锁不变。
"""
import json

def load_options(c, wish_id: int) -> list:
    rows = c.execute(
        "SELECT idx, title, price FROM wish_skus WHERE wish_id=? ORDER BY idx", (wish_id,)
    ).fetchall()
    return [{"idx": r["idx"], "title": r["title"], "price": r["price"]} for r in rows]

def replace_options(c, wish_id: int, options: list) -> None:
    """整表替换某愿望的备选。绝不触碰 wishes.selected_sku 已钉快照。"""
    c.execute("DELETE FROM wish_skus WHERE wish_id=?", (wish_id,))
    c.executemany(
        "INSERT INTO wish_skus(wish_id, idx, title, price) VALUES (?,?,?,?)",
        [(wish_id, o["idx"], o["title"], o["price"]) for o in options],
    )

def options_for_wish(c, row) -> list:
    """有效备选：优先 SKU 行；无行时按遗留规则由标题合成单条。"""
    skus = load_options(c, row["id"])
    if skus:
        return skus
    title = (row["title"] or "").strip()
    if title:
        return [{"idx": 0, "title": title, "price": None, "legacy": True}]
    return []

def parse_selected(row) -> dict | None:
    raw = row.get("selected_sku") if isinstance(row, dict) else row["selected_sku"]
    if not raw:
        return None
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None

def attach_summary(view: dict, row, options: list) -> dict:
    """墙摘要/我的认领：备选个数 + 已钉快照。"""
    view["sku_count"] = len(options)
    view["selected_sku"] = parse_selected(row)
    return view

def attach_detail(view: dict, row, options: list) -> dict:
    """详情：全部备选 + 已钉快照（前端在已认领时只渲染快照，与墙卡一致）。"""
    view["skus"] = options
    view["sku_count"] = len(options)
    view["selected_sku"] = parse_selected(row)
    return view
