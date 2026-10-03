"""多备选 SKU 的校验与编解码。

一条备选形如 {"title": str, "estimated_price": str}（估价允许空串）。
- 发愿望：2~5 条
- 编辑/回填：1~5 条（仅一条时由钉选引擎默认选中，兼容改造前单愿望）
"""
import json

MIN_CREATE, MIN_EDIT, MAX_SKUS = 2, 1, 5
TITLE_MAX, PRICE_MAX = 80, 20

class SkuError(ValueError):
    """携带机器可读 reason 的备选校验错误。"""
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason

def normalize_skus(raw, *, min_count: int = MIN_CREATE, max_count: int = MAX_SKUS) -> list[dict]:
    """校验外部传入的备选列表，返回规整后的 [{title, estimated_price}]。"""
    if not isinstance(raw, list):
        raise SkuError("sku_shape")
    if not (min_count <= len(raw) <= max_count):
        raise SkuError("sku_count")
    out = []
    for item in raw:
        if not isinstance(item, dict):
            raise SkuError("sku_shape")
        title = item.get("title")
        price = item.get("estimated_price", "")
        if not isinstance(title, str) or not title.strip():
            raise SkuError("sku_title_missing")
        title = title.strip()
        if len(title) > TITLE_MAX:
            raise SkuError("sku_title_long")
        if price is None:
            price = ""
        if not isinstance(price, (str, int, float)) or isinstance(price, bool):
            raise SkuError("sku_price_bad")
        price = str(price).strip()
        if len(price) > PRICE_MAX:
            raise SkuError("sku_price_long")
        out.append({"title": title, "estimated_price": price})
    return out

def encode_skus(skus: list[dict]) -> str:
    return json.dumps(skus, ensure_ascii=False, separators=(",", ":"))

def decode_skus(text: str | None) -> list[dict]:
    if not text:
        return []
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    return [d for d in data if isinstance(d, dict) and isinstance(d.get("title"), str)]

def snapshot(skus: list[dict], index: int) -> dict | None:
    """认领时刻的钉选快照；越界返回 None（由钉选引擎拒绝）。"""
    if not isinstance(index, int) or not (0 <= index < len(skus)):
        return None
    s = skus[index]
    return {"title": s["title"], "estimated_price": s.get("estimated_price", ""), "sku_index": index}

def encode_snapshot(snap: dict) -> str:
    return json.dumps(snap, ensure_ascii=False, separators=(",", ":"))

def decode_snapshot(text: str | None) -> dict | None:
    if not text:
        return None
    try:
        d = json.loads(text)
    except (ValueError, TypeError):
        return None
    return d if isinstance(d, dict) and isinstance(d.get("title"), str) else None
