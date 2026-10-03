"""Claim mutex + TTL release for wishes, plus SKU pin-on-claim."""
from datetime import datetime, timedelta, timezone

def parse_ts(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

def claim_allowed(status: str, claimer: str | None, now: datetime, expires_at: str | None) -> dict:
    """Only open wishes (or expired locks) can be claimed."""
    if status == "fulfilled":
        return {"ok": False, "reason": "already_fulfilled"}
    if status == "claimed" and claimer:
        if expires_at and parse_ts(expires_at) <= now:
            return {"ok": True, "reason": "ttl_expired_reclaim"}
        return {"ok": False, "reason": "locked"}
    if status in ("open", "released"):
        return {"ok": True, "reason": ""}
    return {"ok": False, "reason": "bad_status"}

def resolve_pin(options: list, sku_index) -> dict:
    """认领前解析钉选。任何失败都不写锁，调用方直接 409。

    - 零备选：no_sku_options
    - 多备选但未显式指定：sku_required
    - 索引越界/非法：sku_index_out_of_range
    - 仅一条备选时缺省选中第 0 条（兼容改造前单愿望认领）
    """
    if not options:
        return {"ok": False, "reason": "no_sku_options"}
    if sku_index is None:
        if len(options) == 1:
            sku_index = 0
        else:
            return {"ok": False, "reason": "sku_required"}
    if isinstance(sku_index, bool) or not isinstance(sku_index, int):
        return {"ok": False, "reason": "sku_index_out_of_range"}
    if sku_index < 0 or sku_index >= len(options):
        return {"ok": False, "reason": "sku_index_out_of_range"}
    o = options[sku_index]
    return {"ok": True, "selected": {"idx": sku_index, "title": o["title"], "price": o.get("price")}}

def lock_payload(claimer: str, now: datetime, ttl_seconds: int, selected: dict | None = None) -> dict:
    exp = now + timedelta(seconds=ttl_seconds)
    return {
        "status": "claimed",
        "claimer": claimer,
        "claimed_at": now.isoformat(),
        "expires_at": exp.isoformat(),
        "selected_sku": selected,
    }

def release_if_expired(status: str, expires_at: str | None, now: datetime) -> dict | None:
    if status != "claimed" or not expires_at:
        return None
    if parse_ts(expires_at) <= now:
        return {"status": "open", "claimer": None, "claimed_at": None, "expires_at": None,
                "selected_sku": None}
    return None
