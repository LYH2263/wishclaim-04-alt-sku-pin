"""备选 SKU 校验：发愿望/改备选时校验 1~5 条（标题+估价）并归一化。

规则：
- 条数 1~5。多备选是 2~5；单条用于兼容改造前的单愿望认领。
- 标题去空白后非空，长度 <= MAX_TITLE_LEN。
- 估价可为 None（未估价），否则必须是非负有限数值。
"""
import math

MIN_OPTIONS = 1   # 单备选兼容改造前单愿望
MAX_OPTIONS = 5
MAX_TITLE_LEN = 80
MAX_PRICE = 1e12


def _norm_price(raw):
    """None/空串 -> None（未估价）；数值 -> float；其余 -> None 标记非法。"""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None, True
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None, False
    price = float(raw)
    if not math.isfinite(price) or price < 0 or price > MAX_PRICE:
        return None, False
    return price, True


def validate_options(raw) -> dict:
    """校验并归一化备选列表。

    成功：{"ok": True, "options": [{"idx", "title", "price"}, ...]}
    失败：{"ok": False, "reason": <machine_reason>}
    """
    if not isinstance(raw, (list, tuple)):
        return {"ok": False, "reason": "sku_options_not_a_list"}
    if not (MIN_OPTIONS <= len(raw) <= MAX_OPTIONS):
        return {"ok": False, "reason": "sku_count_out_of_range"}
    options = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            return {"ok": False, "reason": "sku_item_invalid"}
        title = str(item.get("title") or "").strip()
        if not title:
            return {"ok": False, "reason": "sku_title_required"}
        if len(title) > MAX_TITLE_LEN:
            return {"ok": False, "reason": "sku_title_too_long"}
        price, ok = _norm_price(item.get("price"))
        if not ok:
            return {"ok": False, "reason": "sku_price_invalid"}
        options.append({"idx": i, "title": title, "price": price})
    return {"ok": True, "options": options}
