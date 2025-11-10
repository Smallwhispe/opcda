import os
import json
import logging
from datetime import datetime, date
from typing import Optional, Any
from zoneinfo import ZoneInfo  # 1. 使用 Python 3.11 内置的 zoneinfo

from vo.ResultEntity import ResultEntity, ResultEntityMethod, ErrorCode

logger = logging.getLogger()
# 2. 使用 zoneinfo 定义时区
LOCAL_TZ = ZoneInfo("Asia/Shanghai")
DATA_DIR = "repository"
EXT = ".ndjson"


# --- 辅助函数 (文件处理) ---
def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def date_to_fname(d: date, data_type: str) -> str:
    """data/<dataType>_YYYY-MM-DD.ndjson"""
    ensure_data_dir()
    fname = "{}_{}{}".format(data_type, d.isoformat(), EXT)
    return os.path.join(DATA_DIR, fname)


# -----------------------------------------------------------------
# !!! 3. 修复: 统一的 Python 3.11+ 解析器 !!!
# -----------------------------------------------------------------
def parse_dt_maybe(value: Any) -> Optional[datetime]:
    """
    [Python 3.11+] 尽力解析任何输入为 datetime 对象。
    - 如果输入带时区 (e.g., +08:00)，则返回带时区的 datetime。
    - 如果输入不带时区 (e.g., 17:00:00)，则返回不带时区的 (naive) datetime。
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value  # 按原样返回
    if isinstance(value, (int, float)):
        try:
            ts_f = float(value)
            if ts_f > 1_000_000_000_000:  # ms
                ts_f = ts_f / 1000.0
            # 返回带本地时区的时间戳
            return datetime.fromtimestamp(ts_f, tz=LOCAL_TZ)
        except Exception:
            return None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            # 替换第一个空格为 'T' 以兼容 ISO 格式 (e.g., "2025-11-10 17:00:00")
            s_iso = s.replace(" ", "T", 1)
            # fromisoformat 会自动保留或省略时区
            return datetime.fromisoformat(s_iso)
        except Exception:
            logger.warning(f"Could not parse time string as ISO: {s}", exc_info=False)
            return None
    return None


def to_local_date(dt: Optional[datetime]) -> Optional[date]:
    """[已修复] 安全地将任何 datetime 转换为本地日期"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # 假定 naive 时间为本地时间
        return dt.date()
    else:
        # 转换 aware 时间为本地时间
        return dt.astimezone(LOCAL_TZ).date()


def pick_file_for_day(data_dt: Optional[datetime], data_type: str) -> Optional[str]:
    """根据 data 指定的日期选择当天文件；找不到返回 None。"""
    if data_dt is None:
        return None
    d = to_local_date(data_dt)
    if d is None:
        return None
    path = date_to_fname(d, data_type)
    return path if os.path.exists(path) else None


# -----------------------------------------------------------------
# !!! 4. DataCollectService 内部实现时间标准化 !!!
# -----------------------------------------------------------------
class DataCollectService:

    @staticmethod
    def _standardize_dt_for_compare(dt: Optional[datetime]) -> Optional[datetime]:
        """
        [内部辅助函数]
        将用于比较的 datetime 对象统一标准化为 LOCAL_TZ。
        """
        if dt is None:
            return None
        if dt.tzinfo is None:
            # 假设所有“无时区”的输入 (来自 Postman) 都是本地时间
            return dt.replace(tzinfo=LOCAL_TZ)
        else:
            # 转换所有“带时区”的输入 (来自文件或UTC查询) 为本地时间
            return dt.astimezone(LOCAL_TZ)

    @staticmethod
    def _get_sort_key(d: dict) -> datetime:
        """[内部辅助函数] 安全地获取排序键"""
        dt = parse_dt_maybe(d.get("time"))
        dt_std = DataCollectService._standardize_dt_for_compare(dt)
        if dt_std:
            return dt_std
        # 将无法解析的记录排在最后
        return datetime.max.replace(tzinfo=LOCAL_TZ)

    @staticmethod
    def data_collect(request) -> ResultEntity:
        """
        [已修复] 读取 data（当天）的文档，返回 [startTime, endTime] 范围内的记录（按时间升序）。
        """
        try:
            data_type = getattr(request, "dataType", None)
            if data_type is None:
                data_type = "default"

            # 1. 解析日期 (使用“只解析”函数)
            date_dt = parse_dt_maybe(getattr(request, "date", None))

            file_path = pick_file_for_day(date_dt, data_type)
            if not file_path:
                logger.info("[data_collect] - 文件不存在: %s", file_path)
                return ResultEntityMethod.buildFailedResult(
                    ErrorCode.NO_DATA.get_code(), ErrorCode.NO_DATA.get_msg(), None
                )

            # 2. 解析起止时间 (使用“只解析”函数)
            start_raw = getattr(request, "startTime", None)
            end_raw = getattr(request, "endTime", None)

            start_dt = parse_dt_maybe(start_raw)
            end_dt = parse_dt_maybe(end_raw)

            # 3. 标准化时间以便比较 (修复点)
            start_dt = DataCollectService._standardize_dt_for_compare(start_dt)
            end_dt = DataCollectService._standardize_dt_for_compare(end_dt)

            logger.info("[data_collect] - 标准化时间窗口: start_dt=%s, end_dt=%s", start_dt, end_dt)

            # 4. 如果两端都为空，默认整天
            if start_dt is None and end_dt is None:
                day = to_local_date(date_dt)
                if day is None:
                    return ResultEntityMethod.buildFailedResult(message="必须提供 date 参数")
                start_dt = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=LOCAL_TZ)
                end_dt = datetime(day.year, day.month, day.day, 23, 59, 59, 999999, tzinfo=LOCAL_TZ)

            if start_dt and end_dt and start_dt > end_dt:
                start_dt, end_dt = end_dt, start_dt

            # 5. 读取当天文件并按窗口过滤
            records = []
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if not s:
                        continue
                    try:
                        obj = json.loads(s)
                    except Exception:
                        continue

                    # 解析文件时间
                    t_dt = parse_dt_maybe(obj.get("time"))
                    # 标准化文件时间
                    t_dt = DataCollectService._standardize_dt_for_compare(t_dt)

                    if t_dt is None:
                        continue

                    # 现在 start_dt, end_dt, t_dt 都在同一个时区 (LOCAL_TZ)
                    if start_dt and t_dt < start_dt:
                        continue
                    if end_dt and t_dt > end_dt:
                        continue
                    records.append(obj)

            # 6. 排序
            records.sort(key=DataCollectService._get_sort_key)

            resp = {"dataList": records, "total": len(records)}
            logger.info(records)
            logger.info(f"[data_collect] - 查询到 {len(records)} 条记录")
            return ResultEntityMethod.buildSuccessResult(data=resp)

        except Exception as e:
            logger.error("[opc本地读取] - data_collect 失败: %s", e, exc_info=True)
            return ResultEntityMethod.buildFailedResult(message="本地数据读取失败")

    @staticmethod
    def data_collect_by_page(request) -> ResultEntity:
        """
        [已修复] 同上，但带分页：
        """
        try:
            data_type = getattr(request, "dataType", None)
            if data_type is None:
                data_type = "default"

            date_dt = parse_dt_maybe(getattr(request, "data", None))

            file_path = pick_file_for_day(date_dt, data_type)
            if not file_path:
                logger.info("[data_collect_by_page] - 文件不存在: %s", file_path)
                return ResultEntityMethod.buildSuccessResult(
                    ErrorCode.NO_DATA.get_code(), ErrorCode.NO_DATA.get_msg(), None
                )

            start_raw = getattr(request, "startTime", None)
            end_raw = getattr(request, "endTime", None)

            start_dt = parse_dt_maybe(start_raw)
            end_dt = parse_dt_maybe(end_raw)

            start_dt = DataCollectService._standardize_dt_for_compare(start_dt)
            end_dt = DataCollectService._standardize_dt_for_compare(end_dt)

            if start_dt is None and end_dt is None:
                day = to_local_date(date_dt)
                if day is None:
                    return ResultEntityMethod.buildFailedResult(message="必须提供 data 参数")
                start_dt = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=LOCAL_TZ)
                end_dt = datetime(day.year, day.month, day.day, 23, 59, 59, 999999, tzinfo=LOCAL_TZ)

            if start_dt and end_dt and start_dt > end_dt:
                start_dt, end_dt = end_dt, start_dt

            records = []
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if not s:
                        continue
                    try:
                        obj = json.loads(s)
                    except Exception:
                        continue

                    t_dt = parse_dt_maybe(obj.get("time"))
                    t_dt = DataCollectService._standardize_dt_for_compare(t_dt)

                    if t_dt is None:
                        continue
                    if start_dt and t_dt < start_dt:
                        continue
                    if end_dt and t_dt > end_dt:
                        continue
                    records.append(obj)

            records.sort(key=DataCollectService._get_sort_key)

            page = getattr(request, 'page', 1)
            size = getattr(request, 'size', 20)
            try:
                page = int(page)
                size = int(size)
            except Exception:
                page, size = 1, 20

            if page < 1:
                page = 1
            if size < 1 or size > 1000:
                size = 20

            start_idx = (page - 1) * size
            end_idx = start_idx + size
            page_items = records[start_idx:end_idx]

            current_page_count = len(page_items)

            if current_page_count == 0:
                logger.info("[opc本地分页] - 未查询到符合条件的数据")
                return ResultEntityMethod.buildFailedResult(
                    ErrorCode.NO_DATA.get_code(),
                    ErrorCode.NO_DATA.get_msg(),
                    None
                )

            resp = {
                "dataList": page_items,
                "total": current_page_count,
            }
            return ResultEntityMethod.buildSuccessResult(data=resp)

        except Exception as e:
            logger.error("[opc本地分页] - 失败: %s", e, exc_info=True)
            return ResultEntityMethod.buildFailedResult(message="本地数据服务暂时不可用")