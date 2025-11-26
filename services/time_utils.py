import logging
from datetime import datetime, date
from typing import Optional, Any
from zoneinfo import ZoneInfo

logger = logging.getLogger()

LOCAL_TZ = ZoneInfo("Asia/Shanghai")

# =========================
# 时间解析
# =========================
def parse_dt_maybe(value: Any) -> Optional[datetime]:
    """解析各种格式的时间输入并返回 datetime"""
    if value is None:
        return None
    """时间是标准格式datatime"""
    if isinstance(value, datetime):
        return value
    """时间是int或者float的时间戳"""
    if isinstance(value, (int, float)):
        try:
            ts_f = float(value)
            if ts_f > 1_000_000_000_000:  # 毫秒
                ts_f /= 1000.0
            return datetime.fromtimestamp(ts_f, tz=LOCAL_TZ)
        except Exception:
            return None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            s_iso = s.replace(" ", "T", 1)
            return datetime.fromisoformat(s_iso)
        except Exception:
            logger.warning(f"Could not parse time string as ISO: {s}", exc_info=False)
            return None
    return None

"""返回当前日期"""
def to_local_date(dt: Optional[datetime]) -> Optional[date]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.date()
    return dt.astimezone(LOCAL_TZ).date()

"""转换时区"""
def standardize_dt(dt: Optional[datetime]) -> Optional[datetime]:
    """把所有 datetime 统一到 LOCAL_TZ，便于比较"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=LOCAL_TZ)
    return dt.astimezone(LOCAL_TZ)

"""转换成时间戳"""
def dt_to_ts(dt: datetime) -> int:
    """datetime → Unix 时间戳（秒）"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=LOCAL_TZ)
    else:
        dt = dt.astimezone(LOCAL_TZ)
    return int(dt.timestamp())

def to_iso_from_ts(ts: int) -> str:
    """把 Unix 秒转成人类可读的 ISO 字符串（含时区）"""
    dt = datetime.fromtimestamp(ts, tz=LOCAL_TZ)
    return dt.isoformat()