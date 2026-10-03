"""只读投影：把 wishes 行投影成墙摘要 / 详情 / 我的认领三种视图。

三路同钉规则（已拍板）：
- 未认领（open/released）：墙卡只露备选个数，详情展开全部备选供选择；
- 认领后（claimed/fulfilled）：墙卡、详情、我的认领都只展示钉选的一条
  selected_sku 快照，其余备选既不列也不灰显，三路保持一致。
发布者增删备选走独立的管理接口，不经过这些只读投影。
"""
from app.modules.sku_options import decode_skus, decode_snapshot

_PINNED_STATUSES = ("claimed", "fulfilled")
_BASE_FIELDS = ("id", "title", "note", "status", "claimer", "claimed_at", "expires_at", "data_quality")

def _base(row: dict) -> dict:
    return {k: row[k] for k in _BASE_FIELDS if k in row}

def _is_pinned(row: dict) -> bool:
    return row.get("status") in _PINNED_STATUSES

def wall_card(row: dict) -> dict:
    """墙摘要：未认领显备选个数；认领后只挂钉选一条。"""
    out = _base(row)
    if _is_pinned(row):
        out["selected_sku"] = decode_snapshot(row.get("selected_sku"))
    else:
        out["sku_count"] = len(decode_skus(row.get("skus")))
    return out

def detail_view(row: dict) -> dict:
    """详情：未认领展开全部备选；认领后仅钉选快照，不返回其余备选。"""
    out = _base(row)
    if _is_pinned(row):
        out["selected_sku"] = decode_snapshot(row.get("selected_sku"))
    else:
        skus = decode_skus(row.get("skus"))
        out["skus"] = skus
        out["sku_count"] = len(skus)
    return out

def claim_view(row: dict) -> dict:
    """我的认领 / 已完成：只认钉选快照，与墙卡、详情同钉。"""
    out = _base(row)
    out["selected_sku"] = decode_snapshot(row.get("selected_sku"))
    return out
