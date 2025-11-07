import os
import json
import logging
from datetime import datetime, date
from typing import Optional

import pytz

from vo.ResultEntity import ResultEntity, ResultEntityMethod, ErrorCode

logger = logging.getLogger()
LOCAL_TZ = pytz.timezone("Asia/Shanghai")
DATA_DIR = "repository"
EXT = ".ndjson"

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def date_to_fname(d: date, data_type: str) -> str:
    """data/<dataType>_YYYY-MM-DD.ndjson"""
    ensure_data_dir()
    fname = "{}_{}{}".format(data_type, d.isoformat(), EXT)
    return os.path.join(DATA_DIR, fname)

def parse_dt_maybe(value) -> Optional[datetime]:
    """将 str/datetime/时间戳 转为带 Asia/Shanghai 时区的 datetime；失败返回 None。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        #是否有时区
        return value if value.tzinfo else LOCAL_TZ.localize(value)
    if isinstance(value, (int, float)):
        # 视为“秒”时间戳；如果传的是毫秒，请先在业务层 / 这里判断并除以 1000
        return datetime.fromtimestamp(float(value), tz=LOCAL_TZ)
    if isinstance(value, str):
        s = value.strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
                    "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d"):
            try:
                dt = datetime.strptime(s, fmt)
                return LOCAL_TZ.localize(dt)
            except Exception:
                continue
        # 简单 ISO 兜底
        try:
            s2 = s.replace("T", " ").replace("Z", "")
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                try:
                    dt = datetime.strptime(s2, fmt)
                    return LOCAL_TZ.localize(dt)
                except Exception:
                    pass
        except Exception:
            pass
    return None

def to_local_date(dt: Optional[datetime]) -> Optional[date]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = LOCAL_TZ.localize(dt)
    else:
        dt = dt.astimezone(LOCAL_TZ)
    return dt.date()

def pick_file_for_day(data_dt: Optional[datetime], data_type: str) -> Optional[str]:
    """根据 data 指定的日期选择当天文件；找不到返回 None。"""
    if data_dt is None:
        return None
    d = to_local_date(data_dt)
    if d is None:
        return None
    path = date_to_fname(d, data_type)
    return path if os.path.exists(path) else None

def parse_epoch_to_dt(ts: Optional[int]) -> Optional[datetime]:
    """把 int 时间戳（秒或毫秒）转为本地时区 datetime。"""
    if ts is None:
        return None
    try:
        ts_f = float(ts)
        # 简单判断是否毫秒
        if ts_f > 1_000_000_000_000:  # > 10^12 视为毫秒
            ts_f = ts_f / 1000.0
        return datetime.fromtimestamp(ts_f, tz=LOCAL_TZ)
    except Exception:
        return None


class DataCollectService:
    @staticmethod
    def data_collect(request) -> ResultEntity:
        """
        读取 data（当天）的文档，返回 [startTime, endTime] 范围内的记录（按时间升序）。
        request: DataCollectReq
          - page/size: 可为空（此接口不分页，若需要分页请用 data_collect_by_page）
          - data: datetime（指定哪一天的文件）
          - startTime, endTime: int（秒或毫秒时间戳）
        """
        try:
            # 文件类型前缀：如需区分类型可改成你的前缀或从 request 里补充
            data_type = getattr(request, "dataType", None)
            if data_type is None:
                data_type = "default"

            # 解析当天文件
            date_dt = getattr(request, "date", None)
            if date_dt is None and isinstance(request, dict):
                date_dt = request.get("date")
            date_dt = parse_dt_maybe(date_dt)

            file_path = pick_file_for_day(date_dt, data_type)
            if not file_path:
                logger.info("[data_collect] - 文件不存在: %s", file_path)
                return ResultEntityMethod.buildFailedResult(
                    ErrorCode.NO_DATA.get_code(), ErrorCode.NO_DATA.get_msg(), None
                )

            # 解析起止时间
            start_raw = getattr(request, "startTime", None)
            end_raw = getattr(request, "endTime", None)
            if (start_raw is None or end_raw is None) and isinstance(request, dict):
                start_raw = start_raw if start_raw is not None else request.get("startTime")
                end_raw = end_raw if end_raw is not None else request.get("endTime")

            start_dt = parse_epoch_to_dt(start_raw)
            end_dt = parse_epoch_to_dt(end_raw)

            # 如果两端都为空，默认整天
            if start_dt is None and end_dt is None:
                # 整天范围：当天 00:00:00 ~ 23:59:59
                day = to_local_date(date_dt)
                start_dt = LOCAL_TZ.localize(datetime(day.year, day.month, day.day, 0, 0, 0))
                end_dt = LOCAL_TZ.localize(datetime(day.year, day.month, day.day, 23, 59, 59))

            # 容错：若颠倒，交换
            if start_dt and end_dt and start_dt > end_dt:
                start_dt, end_dt = end_dt, start_dt

            # 读取当天文件并按窗口过滤
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
                    if t_dt is None:
                        continue
                    if start_dt and t_dt < start_dt:
                        continue
                    if end_dt and t_dt > end_dt:
                        continue
                    records.append(obj)

            # 时间升序
            records.sort(key=lambda d: parse_dt_maybe(d.get("time")) or LOCAL_TZ.localize(datetime.min))

            resp = {"dataList": records, "total": len(records)}
            return ResultEntityMethod.buildSuccessResult(data=resp)

        except Exception as e:
            logger.error("[opc本地读取] - data_collect 失败: %s", e, exc_info=True)
            return ResultEntityMethod.buildFailedResult(message="本地数据读取失败")

    @staticmethod
    def data_collect_by_page(request) -> ResultEntity:
        """
        同上，但带分页：
          - page: 默认 1
          - size: 默认 100，上限 1000
        """
        try:
            data_type = getattr(request, "dataType", None)
            if data_type is None:
                data_type = "default"

            # 当天文件
            date_dt = getattr(request, "data", None)
            if date_dt is None and isinstance(request, dict):
                date_dt = request.get("data")
            date_dt = parse_dt_maybe(date_dt)

            file_path = pick_file_for_day(date_dt, data_type)
            if not file_path:
                logger.info("[data_collect_by_page] - 文件不存在: %s", file_path)
                return ResultEntityMethod.buildSuccessResult(
                    ErrorCode.NO_DATA.get_code(), ErrorCode.NO_DATA.get_msg(), None
                )

            # 窗口
            start_raw = getattr(request, "startTime", None)
            end_raw = getattr(request, "endTime", None)
            if (start_raw is None or end_raw is None) and isinstance(request, dict):
                start_raw = start_raw if start_raw is not None else request.get("startTime")
                end_raw = end_raw if end_raw is not None else request.get("endTime")

            start_dt = parse_epoch_to_dt(start_raw)
            end_dt = parse_epoch_to_dt(end_raw)

            # 整天默认
            if start_dt is None and end_dt is None:
                day = to_local_date(date_dt)
                start_dt = LOCAL_TZ.localize(datetime(day.year, day.month, day.day, 0, 0, 0))
                end_dt = LOCAL_TZ.localize(datetime(day.year, day.month, day.day, 23, 59, 59))

            if start_dt and end_dt and start_dt > end_dt:
                start_dt, end_dt = end_dt, start_dt

            # 读取并过滤
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
                    if t_dt is None:
                        continue
                    if start_dt and t_dt < start_dt:
                        continue
                    if end_dt and t_dt > end_dt:
                        continue
                    records.append(obj)

            # 排序
            records.sort(key=lambda d: parse_dt_maybe(d.get("time")) or LOCAL_TZ.localize(datetime.min))

            # 分页参数
            page = getattr(request, 'page', 1)
            size = getattr(request, 'size', 20)
            if page is None:
                page = 1
            if size is None:
                size = 20
            try:
                page = int(page)
                size = int(size)
            except Exception:
                page, size = 1, 20

            if page < 1:
                page = 1
            if size < 1 or size > 1000:
                size = 20

            # 切片分页
            start_idx = (page - 1) * size
            end_idx = start_idx + size
            page_items = records[start_idx:end_idx]

            # 当前页数量
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
                "total": current_page_count,  # ✅ 只返回当前页数量
            }
            return ResultEntityMethod.buildSuccessResult(data=resp)

        except Exception as e:
            logger.error("[opc本地分页] - 失败: %s", e, exc_info=True)
            return ResultEntityMethod.buildFailedResult(message="本地数据服务暂时不可用")
