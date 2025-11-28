import os
import json
import sqlite3
import logging
from typing import Any, List, Dict, Union
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
            tic1201b      REAL,
            tic1345       REAL,
            ti1306        REAL,
            ti1329        REAL,
            ti1352a       REAL,
            fic1303       REAL,
            fic1309       REAL,
            fi1314        REAL,
            pic1302       REAL,

            quality_info  TEXT,

            -- 联合唯一索引依然保留，防止同一时间点重复写入
            UNIQUE(data_type, ts)
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
    """
    # 1. 获取基础信息
    data_type = data_view.dataType if data_view.dataType else "default"
    dt = parse_dt_maybe(data.get("time"))
    dt = standardize_dt(dt)
    if dt is None:
        logger.debug("insert_one_record: 时间解析失败，忽略该记录: %s", data)
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

        # --- 修改点：SQL 语句增加 id 列 ---
        sql = """
            INSERT OR IGNORE INTO opc_data (
                id, 
                data_type, ts,
                tic1201b, tic1345, ti1306, ti1329, ti1352a,
                fic1303, fic1309, fi1314,
                pic1302,
                quality_info
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        # --- 修改点：参数元组增加 record_id，并使用 .get() 防止 KeyError ---
        cur.execute(sql, (
            record_id,  # 插入 UUID
            data_type,
            ts,
            values_to_insert.get('tic1201b'),
            values_to_insert.get('tic1345'),
            values_to_insert.get('ti1306'),
            values_to_insert.get('ti1329'),
            values_to_insert.get('ti1352a'),
            values_to_insert.get('fic1303'),
            values_to_insert.get('fic1309'),
            values_to_insert.get('fi1314'),
            values_to_insert.get('pic1302'),
            quality_json
        ))
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
        # 1. 转为字典
        item = dict(row)

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
        # 记得查询 quality_info
        cur.execute(f"""
            SELECT data_type, ts,quality_info,
                   tic1201b, tic1345, ti1306, ti1329, ti1352a,
                   fic1303, fic1309, fi1314,
                   pic1302
            FROM opc_data
            WHERE data_type = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (data_type, n))
        rows = cur.fetchall()
    except Exception:
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
        # 显式查询所有数值列 + quality_info
        cur.execute("""
            SELECT id, 
                   data_type, 
                   ts,
                   quality_info,
                   tic1201b, tic1345, ti1306, ti1329, ti1352a,
                   fic1303, fic1309, fi1314,
                   pic1302
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
        cur.execute("""
            SELECT ts, quality_info,
                   tic1201b, tic1345, ti1306, ti1329, ti1352a,
                   fic1303, fic1309, fi1314,
                   pic1302
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
            SELECT ts, quality_info,
                   tic1201b, tic1345, ti1306, ti1329, ti1352a,
                   fic1303, fic1309, fi1314,
                   pic1302
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
