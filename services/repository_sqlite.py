import os
import json
import sqlite3
import logging
from typing import Any, List, Dict, Union, Optional
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from config.Config import config
EXCLUDE_FIELDS = {'id', 'data_type', 'ts', 'quality_info'}
# ==========================================
# 全局配置加载
# ==========================================


TAG_LIST = [tag.strip() for tag in config.OPC_TAGS.split(',') if tag.strip()]
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
DATA_COLUMN_FULLS = TAG_LIST
DATA_COLUMN_SQL_NAMES = [convert_to_col(full) for full in DATA_COLUMN_FULLS]
# 逗号分隔字符串（若为空则为空字符串）
DATA_COLUMNS_COMMA = ", ".join(DATA_COLUMN_SQL_NAMES) if DATA_COLUMN_SQL_NAMES else ""

# =========================
# 1. 初始化 (建表)
# =========================
import os
import sqlite3
import json
import logging
from typing import Optional, List
from datetime import datetime
from zoneinfo import ZoneInfo
from models.DataView import DataView

# 假设这些来自你的 config.py
# TAG_LIST = ["TI1352A.DACA.PV", "TI1329.DACA.PV", ...]

logger = logging.getLogger(__name__)
LOCAL_TZ = ZoneInfo("Asia/Shanghai")
DATA_DIR = "repository"
DB_FILENAME = "history.db"
DB_PATH = os.path.join(DATA_DIR, DB_FILENAME)

# ==========================================
# 0. 动态列名准备 (关键)
# ==========================================
# 保持 TAG_LIST 与 SQL 列名的顺序严格一致
DATA_COLUMN_FULLS = TAG_LIST
DATA_COLUMN_SQL_NAMES = [tag.replace('.', '_') for tag in DATA_COLUMN_FULLS]


# ==========================================
# 1. 初始化 (动态建表)
# ==========================================
def init_opc_db():
    """
    根据配置文件中的 TAG_LIST 动态创建数据库表结构。
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        # 生成动态列定义部分： "TI1352A_DACA_PV REAL, TI1329_DACA_PV REAL, ..."
        # 这里的列名必须和 TAG_LIST 的顺序一一对应
        dynamic_columns_sql = ",\n".join([f"{col} REAL" for col in DATA_COLUMN_SQL_NAMES])

        # 拼接完整的 CREATE TABLE 语句
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS opc_data (
            id            TEXT PRIMARY KEY,      -- UUID
            data_type     TEXT DEFAULT 'default',
            ts            INTEGER NOT NULL,

            -- 动态生成的点位列
            {dynamic_columns_sql},

            quality_info  TEXT,

            UNIQUE (data_type, ts)
        );
        """

        cur.execute(create_table_sql)

        # 创建索引
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_opc_type_ts
        ON opc_data (data_type, ts);
        """)

        conn.commit()
    except Exception as e:
        logger.error(f"Failed to init DB: {e}")
        raise
    finally:
        conn.close()


# ==========================================
# 2. 写入逻辑 (适配 DataView 字典结构)
# ==========================================
def insert_one_record(data_view: DataView) -> None:
    """
    插入一条记录。
    适配新版 DataView: 使用 values 字典而不是硬编码属性。
    """
    # 1. 基础字段处理
    data_type = data_view.dataType if data_view.dataType else "default"

    # DataView.time 已经是 datetime 对象，直接转换
    if not data_view.time:
        logger.warning("Record missing time, skipping.")
        return

    dt = parse_dt_maybe(data_view.time)
    dt = standardize_dt(dt)

    if dt is None:
        logger.debug("insert_one_record: 时间解析失败，忽略该记录: %s", data_view)
        return False

    ts = dt_to_ts(dt)

    record_id = data_view.id  # UUID

    # 2. 动态提取数值
    # 我们必须按照 CREATE TABLE 时 DATA_COLUMN_SQL_NAMES 的顺序来准备 value list
    values_list = []

    # 遍历完整的点位配置列表
    for full_tag in DATA_COLUMN_FULLS:
        # 从 DataView 的 values 字典中获取值
        # 即使 OPC 没读到这个点，DataView 里可能是 None，这里取出来也是 None，正好存入 SQLite 的 NULL
        val = data_view.values.get(full_tag)
        values_list.append(val)

    # 3. 提取质量信息 (直接存整个 qualities 字典)
    quality_json = json.dumps(data_view.qualities, ensure_ascii=False)

    # 4. 执行 SQL
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        # 动态构造 INSERT 语句
        # 列名部分: id, data_type, ts, Col1, Col2, ..., quality_info
        cols_part = ", ".join(DATA_COLUMN_SQL_NAMES)

        # 占位符部分: ?, ?, ?, ?, ?, ..., ?
        # 数量 = 3个固定字段 (id, type, ts) + N个动态点位 + 1个质量字段
        placeholders_count = 3 + len(DATA_COLUMN_SQL_NAMES) + 1
        placeholders_str = ", ".join(["?"] * placeholders_count)

        sql = f"""
            INSERT OR IGNORE INTO opc_data (
                id, data_type, ts, {cols_part}, quality_info
            ) VALUES ({placeholders_str})
        """

        # 构造参数列表，顺序必须严格匹配 SQL
        # [id, type, ts] + [v1, v2, v3...] + [quality_json]
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
    同时将非系统字段聚合到 'values' 字典中
    """
    results = []

    for row in rows:
        # 1. 转为字典 (sqlite3.Row 支持 dict(row))
        try:
            item = dict(row)
        except Exception:
            continue

        # 2. 准备 values 容器 (必须在循环内初始化，否则数据会累积!)
        values_dict = {}

        # 3. 提取点位数据 (遍历 item，把非系统字段塞进 values_dict)
        for key, val in item.items():
            if key not in EXCLUDE_FIELDS:
                # 关键步骤：把 SQL 中的下划线列名转换为点号格式
                # 例如: TI1352A_DACA_PV -> TI1352A.DACA.PV
                values_dict[key] = val

        # 4. [ID] 处理
        record_id = str(item.get('id')) if item.get('id') else None

        # 5. [dataType] 处理
        data_type = str(item.get('data_type')) if item.get('data_type') else None

        # 6. [qualities] 处理
        qualities = {}
        q_str = item.get('quality_info')
        if q_str:
            try:
                qualities = json.loads(q_str)
            except:
                pass

        # 7. [time] 处理
        ts_val = item.get('ts')
        dt = None
        if ts_val:
            try:
                # 兼容毫秒级时间戳
                timestamp_sec = ts_val / 1000.0 if ts_val > 10000000000 else ts_val
                # 转为 datetime 对象，并指定为中国时区
                dt = datetime.fromtimestamp(timestamp_sec, CN_TZ)
            except Exception as e:
                logger.error(f"时间转换出错: {e}")

        # 8. 构建最终对象 (符合 DataView 模型结构)
        data_view_data = {
            "id": record_id,
            "dataType": data_type,
            "time": dt,  # datetime 对象
            "qualities": qualities,  # 字典
            "values": values_dict  # <--- 核心修改：这里放入了刚才收集的点位字典
        }

        results.append(data_view_data)

    # 打印一条日志验证格式
    # if results:
    #     # 为了日志不报错，我们简单打印一下第一条数据的keys
    #     logger.info("_rows_to_dicts - 首条记录结构: keys=%s", list(results[0].keys()))

    return results

def get_recent_n(n: int = 300) -> List[Dict[str, Any]]:
    data_type = "采样数据"
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
    # logger.info("query_by_time_range - data_type=%s, start_ts=%d, end_ts=%d", data_type, start_ts, end_ts)
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
        # logger.info("query_by_time_range - 查询到 %d 条记录", len(rows))
        # logger.info("query_by_time_range - 首条记录: %s", dict(rows[0]) if rows else "无记录")
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
    records = get_recent_n(n=needed_raw)  # 你已有的函数

    # 安全性判断：数据不够 120 条时自动补齐
    if not records:
        return []

    # 每 4 条取 1 条
    picked = records[::4]  # Python 切片步长 4

    # 只取前 30 条即可
    return picked[:30]
