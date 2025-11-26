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
logger = logging.getLogger()
LOCAL_TZ = ZoneInfo("Asia/Shanghai")

DATA_DIR = "repository"
DB_FILENAME = "history.db"
DB_PATH = os.path.join(DATA_DIR, DB_FILENAME)


# =========================
# 初始化
# =========================
def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        # 建表（字段类型按用户要求：除了 quality（bool->int）和 ts 外，其余用 TEXT）
        cur.execute("""
        CREATE TABLE IF NOT EXISTS opc_data (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            data_type     TEXT DEFAULT 'default',
            ts            INTEGER NOT NULL,
            quality       INTEGER,
            temperature   TEXT,
            flow          TEXT,
            pressure      TEXT,
            concentration TEXT,
            payload       TEXT,
            UNIQUE(data_type, ts)
        );
        """)

        # 索引：按 data_type + ts 查询最常用
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_opc_type_ts
        ON opc_data (data_type, ts);
        """)

        # 可选的仅 ts 索引（如果你常按全局时间查询）
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_opc_ts
        ON opc_data (ts);
        """)

        conn.commit()

        # 推荐的 PRAGMA 设置（在生产环境中可在应用启动时执行一次）
        try:
            # WAL 模式能提升读并发（写仍序列化）
            cur.execute("PRAGMA journal_mode=WAL;")
            # 折中设置，既保证一定的安全性也提升性能
            cur.execute("PRAGMA synchronous=NORMAL;")
            cur.execute("PRAGMA temp_store=MEMORY;")
            # cache_size 为负值表示以 KB 为单位的大小（例如 -20000 -> 20000 pages）
            # 但更通用是使用页数：这里我们不强制改 page_size，仅设置 cache_size 以增加缓存
            cur.execute("PRAGMA cache_size = -20000;")  # 约 20k pages（page 默认 4096B -> ~80MB）
            # mmap_size 提升大文件读取速度（如果平台支持）
            cur.execute("PRAGMA mmap_size = 268435456;")  # 256MB
            conn.commit()
        except Exception:
            # 一些 SQLite 构建可能不支持 mmap_size 等 PRAGMA，忽略其错误
            logger.debug("PRAGMA 执行有异常（可能不被支持），继续。", exc_info=True)

    finally:
        conn.close()

# ---------- 写入 ----------
def normalize_quality(q: Any) -> Optional[int]:
    """
    将各种 quality 表示规范为 0/1：
    - 布尔 True -> 1, False -> 0
    - 数字 0 -> 0, 非 0 -> 1
    - 字符串 "true"/"1"/"yes" -> 1, "false"/"0"/"no" -> 0
    - None -> None
    """
    if q is None:
        return None
    if isinstance(q, bool):
        return 1 if q else 0
    if isinstance(q, (int, float)):
        try:
            return 1 if int(q) != 0 else 0
        except Exception:
            return None
    s = str(q).strip().lower()
    if s in ("true", "1", "yes", "y", "t"):
        return 1
    if s in ("false", "0", "no", "n", "f"):
        return 0
    return None

def insert_one_record(data_type: str, data: dict) -> None:
    if data_type is None:
        data_type = "default"

    # 解析时间
    dt = parse_dt_maybe(data.get("time"))
    dt = standardize_dt(dt)
    if dt is None:
        logger.debug("insert_one_record: 时间解析失败，忽略该记录: %s", data)
        return
    ts = dt_to_ts(dt)

    # 处理 quality（boolean -> 存 0/1）
    quality = normalize_quality(data.get("quality"))

    # 其余字段按用户说明为字符串 -> 直接取字符串（如果为 None 则存 NULL）
    def get_str_field(key: str) -> Optional[str]:
        v = data.get(key)
        if v is None:
            return None
        # 保证存入数据库的是字符串（避免直接存 dict/list）
        if isinstance(v, (dict, list)):
            try:
                return json.dumps(v, ensure_ascii=False)
            except Exception:
                return str(v)
        return str(v)

    temperature = get_str_field("temperature") or get_str_field("temp") or get_str_field("value")
    flow = get_str_field("flow")
    pressure = get_str_field("pressure")
    concentration = get_str_field("concentration")

    payload = json.dumps(data, ensure_ascii=False)

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO opc_data
                (data_type, ts, quality, temperature, flow, pressure, concentration, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (data_type, ts, quality, temperature, flow, pressure, concentration, payload))
        conn.commit()
    except Exception:
        logger.exception("insert_one_record 写入失败")
    finally:
        conn.close()

# ---------- 查询：按时间窗口 ----------
def query_by_time_range(data_type: str, start_ts: int, end_ts: int) -> List[Dict[str, Any]]:
    """
    查询 [start_ts, end_ts] 区间内指定 data_type 的记录，按 ts 升序返回。
    返回每条记录为 dict，字段：
      - time (ISO string)
      - ts (int)
      - quality (int or None)
      - temperature, flow, pressure, concentration (原始字符串或 None)
      - payload (原始 JSON 字符串解析为 dict，如果可解析)
    """
    if data_type is None:
        data_type = "default"

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT ts, quality, temperature, flow, pressure, concentration, payload
            FROM opc_data
            WHERE data_type = ?
              AND ts >= ?
              AND ts <= ?
            ORDER BY ts ASC
        """, (data_type, start_ts, end_ts))
        rows = cur.fetchall()
    except Exception:
        logger.exception("query_by_time_range 执行失败")
        rows = []
    finally:
        conn.close()

    results: List[Dict[str, Any]] = []
    for ts, quality, temperature, flow, pressure, concentration, payload in rows:
        rec: Dict[str, Any] = {"time": to_iso_from_ts(ts), "ts": ts, "quality": quality,
                               "temperature": temperature, "flow": flow, "pressure": pressure,
                               "concentration": concentration}
        results.append(rec)
    return results

# ---------- 分页查询 ----------
def query_by_time_range_with_pagination(
    data_type: str,
    start_ts: int,
    end_ts: int,
    page: int,
    size: int
) -> List[Dict[str, Any]]:
    """
    分页查询。page 从 1 开始，size 每页数量（限制 1..1000）。
    返回当前页的记录列表（同 query_by_time_range 的记录结构）。
    """
    if page is None or page < 1:
        page = 1
    try:
        size = int(size)
    except Exception:
        size = 20
    if size < 1 or size > 1000:
        size = 20

    offset = (page - 1) * size
    if data_type is None:
        data_type = "default"

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT ts, quality, temperature, flow, pressure, concentration, payload
            FROM opc_data
            WHERE data_type = ?
              AND ts >= ?
              AND ts <= ?
            ORDER BY ts ASC
            LIMIT ? OFFSET ?
        """, (data_type, start_ts, end_ts, size, offset))
        rows = cur.fetchall()
    except Exception:
        logger.exception("query_by_time_range_with_pagination 执行失败")
        rows = []
    finally:
        conn.close()

    results: List[Dict[str, Any]] = []
    for ts, quality, temperature, flow, pressure, concentration, payload in rows:
        rec: Dict[str, Any] = {"time": to_iso_from_ts(ts), "ts": ts, "quality": quality,
                               "temperature": temperature, "flow": flow, "pressure": pressure,
                               "concentration": concentration}
        results.append(rec)

    return results

# ---------- 可选工具：按页/按天获取最近 N 条（便于趋势展示） ----------
def get_recent_n(data_type: str, n: int = 300) -> List[Dict[str, Any]]:
    """
    取最近 n 条（最新在后），适合画趋势图（会按 ts 升序返回）
    """
    if data_type is None:
        data_type = "default"
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT ts, quality, temperature, flow, pressure, concentration, payload
            FROM opc_data
            WHERE data_type = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (data_type, n))
        rows = cur.fetchall()
    except Exception:
        logger.exception("get_recent_n 执行失败")
        rows = []
    finally:
        conn.close()

    # rows 是降序，转换并逆序返回升序
    tmp: List[Dict[str, Any]] = []
    for ts, quality, temperature, flow, pressure, concentration, payload in rows:
        rec = {
            "time": to_iso_from_ts(ts),
            "ts": ts,
            "quality": quality,
            "temperature": temperature,
            "flow": flow,
            "pressure": pressure,
            "concentration": concentration
        }
        try:
            rec["payload"] = json.loads(payload) if payload else None
        except Exception:
            rec["payload"] = payload
        tmp.append(rec)
    tmp.reverse()
    return tmp