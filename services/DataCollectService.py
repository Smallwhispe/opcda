import logging
import socket
from datetime import datetime
from zoneinfo import ZoneInfo
from services.predict_result import query_predict_by_time_range, get_recent_n
from services.time_utils import parse_dt_maybe, standardize_dt, dt_to_ts
from services.repository_sqlite import (
    query_by_time_range,
    query_by_time_range_with_pagination,
)

from vo.ResultEntity import ResultEntity, ResultEntityMethod, ErrorCode
from config.Config import Config
logger = logging.getLogger(__name__)
LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def is_port_open(ip: str, port: int, timeout: float = 2.0) -> bool:
    """
    检测指定 IP 和端口是否可达 (TCP)
    :param ip: 目标 IP
    :param port: 目标端口
    :param timeout: 超时时间 (秒)
    :return: True 可达, False 不可达
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        # connect_ex 返回 0 表示成功，其他表示失败（如 10061 拒绝连接）
        result = s.connect_ex((ip, int(port)))
        if result == 0:
            return True
        else:
            logger.warning(f"端口检测失败: {ip}:{port} (ErrCode: {result})")
            return False
    except Exception as e:
        logger.warning(f"端口检测异常: {ip}:{port} - {e}")
        return False
    finally:
        s.close()
class DataCollectService:

    @staticmethod
    def data_collect(request) -> ResultEntity:
        """SQLite 版查询"""
        try:
            data_type = getattr(request, "dataType", None) or "default"

            start_raw = getattr(request, "startTime", None)
            end_raw = getattr(request, "endTime", None)

            start_dt = standardize_dt(parse_dt_maybe(start_raw))
            end_dt = standardize_dt(parse_dt_maybe(end_raw))

            # logger.info("[data_collect] - 标准化时间窗口: start_dt=%s, end_dt=%s", start_dt, end_dt)

            if not start_dt :
                # 没有start → 返回空
                return ResultEntityMethod.buildSuccessResult(message="没有开始时间", data={
                    "dataList": [],
                    "total": 0
                })

            if start_dt and not end_dt:
                # 只有 start → 自动补 end = 当前时间
                end_dt = datetime.now()

            if start_dt and end_dt and start_dt > end_dt:
                start_dt, end_dt = end_dt, start_dt

            start_ts = dt_to_ts(start_dt)
            end_ts   = dt_to_ts(end_dt)

            records = query_by_time_range(data_type, start_ts, end_ts)
            # logger.info("[data_collect] - 查询结果样例: %s", records[:5])
            return ResultEntityMethod.buildSuccessResult(data={
                "dataList": records,
                "total": len(records)
            })

        except Exception:
            logger.exception("[SQLite] data_collect 失败")
            return ResultEntityMethod.buildFailedResult(message="本地数据读取失败")

    @staticmethod
    def data_collect_by_page(request) -> ResultEntity:
        """SQLite 版分页查询"""
        try:
            data_type = getattr(request, "dataType", None) or "default"

            start_raw = getattr(request, "startTime", None)
            end_raw = getattr(request, "endTime", None)

            start_dt = standardize_dt(parse_dt_maybe(start_raw))
            end_dt   = standardize_dt(parse_dt_maybe(end_raw))

            if not start_dt:
                # 没有start → 返回空
                return ResultEntityMethod.buildSuccessResult(message="没有开始时间", data={
                    "dataList": [],
                    "total": 0
                })

            if start_dt and not end_dt:
                # 只有 start → 自动补 end = 当前时间
                end_dt = datetime.now()

            if start_dt and end_dt and start_dt > end_dt:
                start_dt, end_dt = end_dt, start_dt

            start_ts = dt_to_ts(start_dt)
            end_ts   = dt_to_ts(end_dt)

            # 分页参数
            page = int(getattr(request, "page", 1))
            size = int(getattr(request, "size", 20))

            records = query_by_time_range_with_pagination(
                data_type, start_ts, end_ts, page, size
            )

            if not records:
                return ResultEntityMethod.buildFailedResult(
                    ErrorCode.NO_DATA.get_code(), ErrorCode.NO_DATA.get_msg(), None
                )

            return ResultEntityMethod.buildSuccessResult(data={
                "dataList": records,
                "total": len(records)
            })

        except Exception:
            logger.exception("[SQLite] data_collect_by_page 失败")
            return ResultEntityMethod.buildFailedResult(message="本地数据服务不可用")

    @staticmethod
    def predict_result(request) -> ResultEntity:
        """SQLite 版查询"""
        try:

            start_raw = getattr(request, "startTime", None)
            end_raw = getattr(request, "endTime", None)

            start_dt = standardize_dt(parse_dt_maybe(start_raw))
            end_dt = standardize_dt(parse_dt_maybe(end_raw))

            # logger.info("[predict_result] - 标准化时间窗口: start_dt=%s, end_dt=%s", start_dt, end_dt)

            if not start_dt :
                # 没有start → 返回空
                return ResultEntityMethod.buildSuccessResult(message="没有开始时间", data={
                    "dataList": [],
                    "total": 0
                })

            if start_dt and not end_dt:
                # 只有 start → 自动补 end = 当前时间
                end_dt = datetime.now()

            if start_dt and end_dt and start_dt > end_dt:
                start_dt, end_dt = end_dt, start_dt

            start_ts = dt_to_ts(start_dt)
            end_ts   = dt_to_ts(end_dt)

            records = query_predict_by_time_range(start_ts, end_ts)
            # logger.info("[predict_result] - 查询结果样例: %s", records[:5])
            return ResultEntityMethod.buildSuccessResult(data={
                "dataList": records,
                "total": len(records)
            })

        except Exception:
            logger.exception("[SQLite] predict_result 失败")
            return ResultEntityMethod.buildFailedResult(message="本地数据读取失败")

    @staticmethod
    def predict_one() -> ResultEntity:
        # if is_port_open(Config.IP,Config.PORT):
        #     try:
        #         records = get_recent_n(1)
        #         # logger.info("[predict_result] - 查询结果样例: %s", records[:5])
        #         return ResultEntityMethod.buildSuccessResult(data={
        #             "dataList": records,
        #             "total": len(records)
        #         })
        #
        #     except Exception:
        #         logger.exception("[SQLite] predict_result 失败")
        #         return ResultEntityMethod.buildFailedResult(message="本地数据读取失败")
        # else:
        #     return ResultEntityMethod.buildFailedResult(message="本地数据服务不可用")
        try:
            records = get_recent_n(1)
            logger.info("[predict_result] - 查询最新的一条: %s", records[:5])
            return ResultEntityMethod.buildSuccessResult(data={
                "dataList": records,
                "total": len(records)
            })

        except Exception:
            logger.exception("[SQLite] predict_result 失败")
            return ResultEntityMethod.buildFailedResult(message="本地数据读取失败")