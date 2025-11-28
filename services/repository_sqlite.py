import os
import json
import sqlite3
import logging
from typing import Any, List, Dict, Union, Optional
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()
# ==========================================
# 全局配置加载
# ==========================================
def load_tag_map():
    """
    从 .env 读取并解析 OPC_TAG_MAP
    返回格式: [('tic1201b', 'TIC1201B.PIDA.PV'), ...]
    """
    raw_json = os.getenv("OPC_TAG_MAP", "{}")
    try:
        tag_dict = json.loads(raw_json)
        # 将字典转换为列表元组，适配原有代码逻辑
        return list(tag_dict.items())
    except json.JSONDecodeError as e:
        logger.error(f"❌ 解析 .env 中的 OPC_TAG_MAP 失败: {e}")
        # 如果解析失败，返回空列表或硬编码的默认值作为兜底
        return []

GLOBAL_TAG_MAP = load_tag_map()
import time
from models.DataView import DataView
# 假设 services.time_utils 依然存在
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


# ---------- 辅助函数（将 full tag 转为 SQL 列名） ----------
def convert_to_col(full_tag_name: str) -> Optional[str]:
    """
    将 OPC 全名（例如 'TIC1201B.PIDA.PV'）转换为 SQL 列名（'TIC1201B_PIDA_PV'）
    保持大小写，不做小写化。
    """
    if full_tag_name is None:
        return None
    return full_tag_name.replace('.', '_')

def convert_to_arg(tag: str) -> str:
    """
    将 'TIC1201B.PIDA.PV' 转换为 'ARG2_TIC1201B_PV'
    """
    parts = tag.split(".")
    middle = parts[0]
    return f"ARG2_{middle}_PV"

def col_to_arg(tag: str) -> str:
    """
    将 TIC1201B_PIDA_PV 或 TIC1201B_DACA_PV 转为 ARG2_TIC1201B_PV
    """
    middle = tag.split("_")[0]
    return f"ARG2_{middle}_PV"

def arg_to_col(tag: str) -> str:
    """
    将 ARG2_TIC1201B_PV 转换为 TIC1201B_PIDA_PV / TIC1201B_DACA_PV
    按规则：带 C → PIDA，不带 C → DACA
    """
    middle = tag.replace("ARG2_", "").replace("_PV", "")
    if "C" in middle:
        mode = "PIDA"
    else:
        mode = "DACA"
    return f"{middle}_{mode}_PV"
# 预构造数据列名列表（基于 GLOBAL_TAG_MAP），便于复用在 SELECT/INSERT 中
DATA_COLUMN_FULLS = [full for (_attr, full) in GLOBAL_TAG_MAP]
DATA_COLUMN_SQL_NAMES = [convert_to_col(full) for full in DATA_COLUMN_FULLS]
# 逗号分隔字符串（若为空则为空字符串）
DATA_COLUMNS_COMMA = ", ".join(DATA_COLUMN_SQL_NAMES) if DATA_COLUMN_SQL_NAMES else ""

# =========================
# 1. 初始化 (建表)
# =========================
def init_opc_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        # ⚠️ 必须先删除旧表，因为主键定义变了
        # cur.execute("DROP TABLE IF EXISTS opc_data;")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS opc_data (
            id            TEXT PRIMARY KEY,      -- 直接存储 UUID，不自增
            data_type     TEXT DEFAULT 'default',
            ts            INTEGER NOT NULL,

                        -- 数值列
                        TI1352A_DACA_PV  REAL,
                        TI1329_DACA_PV   REAL,
                        TI1328_DACA_PV   REAL,
                        PIC1306_PIDA_PV  REAL,
                        TI1338_DACA_PV   REAL,
                        FIC1308_PIDA_PV  REAL,
                        FIC1309_PIDA_PV  REAL,
                        FIC1310_PIDA_PV  REAL,
                        FIC1303_PIDA_PV  REAL,
                        FIC1311_PIDA_PV  REAL,
                        TI1330_DACA_PV   REAL,
                        TIC1201B_PIDA_PV REAL,
                        PI1204_DACA_PV   REAL,
                        FIC1214_PIDA_PV  REAL,
                        FI1160_DACA_PV   REAL,
                        FIC1210_PIDA_PV  REAL,
                        FIC1203_PIDA_PV  REAL,
                        FI1405_DACA_PV   REAL,
                        FI1314_DACA_PV   REAL,
                        FI1312_DACA_PV   REAL,
                        PI1308_DACA_PV   REAL,
                        TI1304_DACA_PV   REAL,
                        TIC1345_PIDA_PV  REAL,
                        FIC1307_PIDA_PV  REAL,
                        FIC1306_PIDA_PV  REAL,
                        FIC1305_PIDA_PV REAL,
                        FIC1304_PIDA_PV REAL,
                        PI1304_DACA_PV  REAL,
                        TI1308_DACA_PV  REAL,
                        TI1310_DACA_PV  REAL,
                        TI1312_DACA_PV  REAL,
                        TI1314_DACA_PV  REAL,
                        TI1341_DACA_PV  REAL,
                        TI1347_DACA_PV  REAL,
                        TIC1101_PIDA_PV REAL,
                        TIC1103_PIDA_PV REAL,
                        TI1233C_PIDA_PV REAL,
                        TI1306_DACA_PV  REAL,

                        quality_info    TEXT,

                        UNIQUE (data_type, ts)
                    );
                    """)

        # 索引
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_opc_type_ts
        ON opc_data (data_type, ts);
        """)

        conn.commit()
    finally:
        conn.close()


# =========================
# 2. 写入逻辑
# =========================
def insert_one_record(data_view: DataView) -> None:
    """
    插入一条记录。
    已修改：直接使用 DataView.id (UUID) 作为主键插入，不使用自增 ID。
    关键修改：INSERT 的列名与参数根据 GLOBAL_TAG_MAP 动态构造，避免硬编码旧列名。
    """
    # 1. 获取基础信息
    data_type = data_view.dataType if data_view.dataType else "default"
    dt = parse_dt_maybe(data_view.get("time"))
    dt = standardize_dt(dt)
    if dt is None:
        logger.debug("insert_one_record: 时间解析失败，忽略该记录: %s", data_view)
        return False
    ts = dt_to_ts(dt)

    # --- 新增：获取 UUID ---
    record_id = data_view.id

    # 2. 获取映射配置
    tag_map = GLOBAL_TAG_MAP

    values_to_insert = {}
    quality_map = {}

    for attr_name, full_tag_name in tag_map:
        # A. 提取数值
        # getattr 安全获取，如果 DataView 缺少该属性则返回 None
        raw_val = getattr(data_view, attr_name, None)
        try:
            val = float(raw_val) if raw_val is not None else None
        except (ValueError, TypeError):
            val = None
        values_to_insert[attr_name] = val

        # B. 提取质量
        qual = data_view.qualities.get(full_tag_name, 'Bad')
        quality_map[full_tag_name] = str(qual)

    # 3. 序列化质量信息
    quality_json = json.dumps(quality_map, ensure_ascii=False)

    # 4. 执行 SQL
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        # 构造数据列名列表（SQL 列名，如 "TIC1201B_PIDA_PV"）
        sql_col_names = [convert_to_col(full_tag) for (_attr, full_tag) in tag_map]
        # 组合成 "col1, col2, col3" 字符串
        cols_part = ", ".join(sql_col_names)
        # 占位符参数个数（?）
        placeholders = ", ".join(["?"] * len(sql_col_names))

        # 完整 SQL：id, data_type, ts, <cols_part>, quality_info
        sql = f"""
            INSERT OR IGNORE INTO opc_data (
                id,
                data_type,
                ts,
                {cols_part},
                quality_info
            ) VALUES (?, ?, ?, {placeholders}, ?)
        """

        # 构建参数列表：record_id, data_type, ts, <values in same order as sql_col_names>, quality_json
        values_list = [values_to_insert.get(attr) for (attr, _full) in tag_map]
        params = [record_id, data_type, ts] + values_list + [quality_json]

        cur.execute(sql, params)
        conn.commit()
    except Exception as e:
        logger.exception(f"insert_one_record error: {e}")
    finally:
        conn.close()


# =========================
# 3. 查询逻辑
# =========================
# 定义中国时区 (UTC+8)
from datetime import datetime, timezone, timedelta
CN_TZ = timezone(timedelta(hours=8))


def _rows_to_dicts(rows: list) -> list:
    """
    将数据库行转为 JSON 字典，并将时间戳转换为中国格式时间
    """
    results = []

    for row in rows:
        # 1. 转为字典（sqlite3.Row 支持 dict(row)）
        try:
            item = dict(row)
        except Exception:
            # 如果 row 是 tuple，则无法直接转 dict，此时跳过（但按你的原逻辑应使用 Row）
            continue

        # 2. [ID] 处理
        if item.get('id'):
            item['id'] = str(item['id'])

        # 3. [dataType] 处理
        raw_type = item.pop('data_type', None)
        item['dataType'] = str(raw_type) if raw_type else None

        # 4. [qualities] 处理
        q_str = item.pop('quality_info', None)
        item['qualities'] = {}
        if q_str:
            try:
                item['qualities'] = json.loads(q_str)
            except:
                pass

        # 5. [time] 处理 (核心修改)
        ts_val = item.pop('ts', None)
        item['time'] = None

        if ts_val:
            try:
                # 兼容毫秒级时间戳
                timestamp_sec = ts_val / 1000.0 if ts_val > 10000000000 else ts_val

                # 1. 转为 datetime 对象，并指定为中国时区
                dt = datetime.fromtimestamp(timestamp_sec, CN_TZ)

                # 2. 【关键修改在这里】
                item['time'] = dt

            except Exception as e:
                logger.error(f"时间转换出错: {e}")
                item['time'] = str(ts_val)

        results.append(item)

    # 打印一条日志验证格式
    if results:
        logger.info("首条时间结果: %s", results[0].get('time'))

    return results

def get_recent_n(data_type: str, n: int = 300) -> List[Dict[str, Any]]:
    if data_type is None: data_type = "default"
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        # 如果没有任何配置的列，则只选基础列
        select_cols = DATA_COLUMNS_COMMA
        if select_cols:
            select_clause = f"ts, quality_info, {select_cols}"
        else:
            select_clause = "ts, quality_info"

        cur.execute(f"""
            SELECT {select_clause}
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

    results = _rows_to_dicts(rows)
    results.reverse()
    return results

def query_by_time_range(data_type: str, start_ts: int, end_ts: int) -> List[Dict[str, Any]]:
    """
    按时间范围查询 (ts >= start AND ts <= end)
    """
    if data_type is None:
        data_type = "default"
    logger.info("query_by_time_range - data_type=%s, start_ts=%d, end_ts=%d", data_type, start_ts, end_ts)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 必须开启，以便通过列名访问
    try:
        cur = conn.cursor()
        # 构造 SELECT 列
        select_cols = DATA_COLUMNS_COMMA
        if select_cols:
            select_clause = f"id, data_type, ts, quality_info, {select_cols}"
        else:
            select_clause = "id, data_type, ts, quality_info"

        cur.execute(f"""
            SELECT {select_clause}
            FROM opc_data
            WHERE data_type = ?
              AND ts >= ?
              AND ts <= ?
            ORDER BY ts ASC
        """, (data_type, start_ts, end_ts))
        rows = cur.fetchall()
        logger.info("query_by_time_range - 查询到 %d 条记录", len(rows))
        logger.info("query_by_time_range - 首条记录: %s", dict(rows[0]) if rows else "无记录")
    except Exception:
        logger.exception("query_by_time_range 执行失败")
        rows = []
    finally:
        conn.close()

    return _rows_to_dicts(rows)


def query_by_time_range_with_pagination(
    data_type: str,
    start_ts: int,
    end_ts: int,
    page: int,
    size: int
) -> List[Dict[str, Any]]:
    """
    分页查询 (LIMIT ... OFFSET ...)
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
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()

        select_cols = DATA_COLUMNS_COMMA
        if select_cols:
            select_clause = f"ts, quality_info, {select_cols}"
        else:
            select_clause = "ts, quality_info"

        cur.execute(f"""
            SELECT {select_clause}
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

    return _rows_to_dicts(rows)

# ---------- 可选工具：按页/按天获取最近 N 条（便于趋势展示） ----------
def get_every_four_pick_thirty() -> List[Dict[str, Any]]:
    """
    从最新数据中每 4 条取 1 条，最终取 30 条
    = 需要获取最近 120 条
    """
    needed_raw = 30 * 4  # 120 条
    records = get_recent_n(data_type="采样数据", n=needed_raw)  # 你已有的函数

    # 安全性判断：数据不够 120 条时自动补齐
    if not records:
        return []

    # 每 4 条取 1 条
    picked = records[::4]  # Python 切片步长 4

    # 只取前 30 条即可
    return picked[:30]
