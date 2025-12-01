import os
import json
import sqlite3
import logging
from typing import Any, List, Dict
from typing import Optional
from zoneinfo import ZoneInfo

from services.time_utils import (
    parse_dt_maybe,
    standardize_dt,
    dt_to_ts,
    to_iso_from_ts
)

logger = logging.getLogger(__name__)
LOCAL_TZ = ZoneInfo("Asia/Shanghai")

DATA_DIR = "repository"
DB_FILENAME = "history.db"
DB_PATH = os.path.join(DATA_DIR, DB_FILENAME)


# =========================
# 初始化
# =========================
def init_predict_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        # --- 创建 predict 表 ---
        cur.execute("""
        CREATE TABLE IF NOT EXISTS predict (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            pressure  TEXT,
            ts        INTEGER NOT NULL,
            c5        TEXT,
            bing_xi   TEXT,
            gan_dian  TEXT,
            payload   TEXT,
            UNIQUE(ts)
        );
        """)

        # 索引：按 ts 查询高频
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_predict_ts
        ON predict (ts);
        """)

        conn.commit()

        # 性能优化 PRAGMA（与您原代码保持一致）
        try:
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA synchronous=NORMAL;")
            cur.execute("PRAGMA temp_store=MEMORY;")
            cur.execute("PRAGMA cache_size = -20000;")  # ~80MB cache
            cur.execute("PRAGMA mmap_size = 268435456;")  # 256 MB
            conn.commit()
        except Exception:
            logger.debug("PRAGMA 不支持或有异常。", exc_info=True)

    finally:
        conn.close()


# ---------- 写入 ----------
def get_str_field(v: Any) -> Optional[str]:
    """将任意字段规范为 TEXT（字符串）"""
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        try:
            return json.dumps(v, ensure_ascii=False)
        except Exception:
            return str(v)
    return str(v)


def insert_predict_record(data: dict) -> bool:
    # ---- 解析时间 ----
    dt = standardize_dt(parse_dt_maybe(data.get("time")))
    if dt is None:
        logger.debug("insert_predict_record: 时间解析失败: %s", data)
        return False

    ts = dt_to_ts(dt)

    pressure = get_str_field(data.get("pressure"))
    c5 = get_str_field(data.get("c5"))
    bing_xi = get_str_field(data.get("bing_xi"))
    gan_dian = get_str_field(data.get("gan_dian"))

    payload = json.dumps(data, ensure_ascii=False)

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO predict
                (pressure, ts, c5, bing_xi, gan_dian, payload)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (pressure, ts, c5, bing_xi, gan_dian, payload))
        conn.commit()
    except Exception:
        logger.exception("insert_predict_record 写入失败")
        return False
    finally:
        conn.close()
        return True


# ---------- 查询（按时间范围） ----------
def query_predict_by_time_range(start_ts: int, end_ts: int) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT ts, pressure, c5, bing_xi, gan_dian, payload
            FROM predict
            WHERE ts >= ? AND ts <= ?
            ORDER BY ts ASC
        """, (start_ts, end_ts))
        rows = cur.fetchall()
    except Exception:
        logger.exception("query_by_time_range 执行失败")
        rows = []
    finally:
        conn.close()

    results = []
    for ts, pressure, c5, bing_xi, gan_dian, payload in rows:
        rec = {
            "time": to_iso_from_ts(ts),
            "ts": ts,
            "pressure": pressure,
            "c5": c5,
            "bing_xi": bing_xi,
            "gan_dian": gan_dian,
        }
        try:
            rec["payload"] = json.loads(payload) if payload else None
        except Exception:
            rec["payload"] = payload
        results.append(rec)

    return results


# ---------- 分页查询 ----------
def query_by_time_range_with_pagination(start_ts: int, end_ts: int, page: int, size: int):
    if page < 1:
        page = 1

    size = max(1, min(int(size), 1000))  # size 1..1000

    offset = (page - 1) * size

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT ts, pressure, c5, bing_xi, gan_dian, payload
            FROM predict
            WHERE ts >= ? AND ts <= ?
            ORDER BY ts ASC
            LIMIT ? OFFSET ?
        """, (start_ts, end_ts, size, offset))
        rows = cur.fetchall()
    except Exception:
        logger.exception("query_by_time_range_with_pagination 执行失败")
        rows = []
    finally:
        conn.close()

    results = []
    for ts, pressure, c5, bing_xi, gan_dian, payload in rows:
        rec = {
            "time": to_iso_from_ts(ts),
            "ts": ts,
            "pressure": pressure,
            "c5": c5,
            "bing_xi": bing_xi,
            "gan_dian": gan_dian
        }
        try:
            rec["payload"] = json.loads(payload) if payload else None
        except Exception:
            rec["payload"] = payload
        results.append(rec)

    return results


# ---------- 最近 N 条 ----------
def get_recent_n(n: int = 300) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT ts, pressure, c5, bing_xi, gan_dian, payload
            FROM predict
            ORDER BY ts DESC
            LIMIT ?
        """, (n,))
        rows = cur.fetchall()
    except Exception:
        logger.exception("get_recent_n 执行失败")
        rows = []
    finally:
        conn.close()

    tmp = []
    for ts, pressure, c5, bing_xi, gan_dian, payload in rows:
        rec = {
            "time": to_iso_from_ts(ts),
            "ts": ts,
            "pressure": pressure,
            "c5": c5,
            "bing_xi": bing_xi,
            "gan_dian": gan_dian,
        }
        try:
            rec["payload"] = json.loads(payload) if payload else None
        except Exception:
            rec["payload"] = payload
        tmp.append(rec)

    # 逆序成升序
    tmp.reverse()
    return tmp

def get_latest_record_simple() -> Optional[Dict[str, Any]]:
    """
    使用现有的 get_recent_n 函数来获取最新记录
    """
    records = get_recent_n(1)
    return records[0] if records else None