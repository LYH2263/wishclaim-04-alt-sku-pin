"""钉选写锁引擎：认领必须显式选中一条备选，快照随互斥锁原子落库。

与 claim_lock（互斥/TTL）分工：
- claim_lock 决定「能不能认」并给出锁字段；
- sku_pin 决定「认哪一条」并给出 selected_sku 快照；
- main 把两者合并为同一条 UPDATE，保证锁与快照同生共死。
"""
from app.modules.sku_options import snapshot

def resolve_pin(skus: list[dict], sku_index) -> dict:
    """根据备选列表和请求给出的索引裁决钉选。

    返回 {"ok": True, "snapshot": {...}} 或 {"ok": False, "reason": ...}。
    - 零备选：sku_none
    - 越界（含负数/非整数）：sku_index_bad
    - 多条备选且未显式给出索引：sku_selection_required
    - 仅一条且未给索引：默认选中第 0 条，兼容改造前的单愿望认领
    """
    if not skus:
        return {"ok": False, "reason": "sku_none"}
    if sku_index is None:
        if len(skus) == 1:
            return {"ok": True, "snapshot": snapshot(skus, 0)}
        return {"ok": False, "reason": "sku_selection_required"}
    if isinstance(sku_index, bool) or not isinstance(sku_index, int):
        return {"ok": False, "reason": "sku_index_bad"}
    snap = snapshot(skus, sku_index)
    if snap is None:
        return {"ok": False, "reason": "sku_index_bad"}
    return {"ok": True, "snapshot": snap}
