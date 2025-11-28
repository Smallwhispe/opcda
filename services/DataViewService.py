import logging
import os
import qrcode
import csv

from models.DataView import DataView
from services.time_utils import parse_dt_maybe, standardize_dt, dt_to_ts
from services.repository_sqlite import (
    insert_one_record,
    query_by_time_range,
    query_by_time_range_with_pagination,
)
from vo.ResultEntity import ResultEntity
from vo.QrExport import QrExportRes, QrExportReq
from vo.ResultEntity import ResultEntityMethod
from vo.req import ModelPredictReq, DataExportReq, QrQueryReq
from vo.res import QrQueryRes

from datetime import datetime

import pytz
logger = logging.getLogger(__name__)
LOCAL_TZ = pytz.timezone("Asia/Shanghai")

DATA_DIR = "repository"
EXT = ".ndjson"
EXPORT_DIR = "export"

class DataViewService:
    @staticmethod
    def data_export(request: 'DataExportReq') -> ResultEntity:
        try:
            # 1) dataType
            data_type = getattr(request, "dataType", None) or "default"
            if data_type is None and isinstance(request, dict):
                data_type = request.get("dataType")
            if not data_type:
                data_type = "default"

            # 2) 解析 startDate / endDate（可能为空）
            start_raw = getattr(request, "startDate", None)
            end_raw = getattr(request, "endDate", None)
            if start_raw is None and isinstance(request, dict):
                start_raw = request.get("startDate")
            if end_raw is None and isinstance(request, dict):
                end_raw = request.get("endDate")

            start_dt = standardize_dt(parse_dt_maybe(start_raw))
            end_dt = standardize_dt(parse_dt_maybe(end_raw))
            logger.info("[data_preview] - 标准化时间窗口: start_dt=%s, end_dt=%s", start_dt, end_dt)

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
            end_ts = dt_to_ts(end_dt)

            try:
                preview_records = query_by_time_range_with_pagination(
                    data_type, start_ts, end_ts, page=1, size=100
                )
            except Exception as e:
                logger.exception("[opc数据预览 - SQLite] 查询失败: %s", e)
                return ResultEntityMethod.buildFailedResult(message="数据库查询失败")

            logger.info("[opc数据预览] - 预览获取成功 (返回 %d 条)", len(preview_records))

            # ----------------------------------------------------------------------
            # 4) 查询全部数据用于 CSV 导出
            # ----------------------------------------------------------------------
            try:
                full_records = query_by_time_range(data_type, start_ts, end_ts)
            except Exception as e:
                logger.exception("[opc数据预览 - SQLite] 全量查询失败 %s", e)
                return ResultEntityMethod.buildFailedResult(message="数据库全量查询失败")

            # ----------------------------------------------------------------------
            # 5) 生成 CSV 文件
            # ----------------------------------------------------------------------
            export_dir = os.path.join(os.getcwd(), "export")
            os.makedirs(export_dir, exist_ok=True)

            file_name = f"{data_type}_{datetime.now().strftime('%Y%m%d_%H:%M:%S')}.csv"
            file_path = os.path.join(export_dir, file_name)

            try:
                with open(file_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)

                    # 写表头（根据第一条记录来生成）
                    if full_records:
                        writer.writerow(full_records[0].keys())

                    # 写数据
                    for row in full_records:
                        writer.writerow(row.values())

            except Exception as e:
                logger.exception("[opc数据预览 - CSV导出错误] %s", e)
                return ResultEntityMethod.buildFailedResult(message="CSV导出失败")

            logger.info("[opc数据预览] - CSV 导出成功: %s", file_path)

            # ----------------------------------------------------------------------
            # 6) 返回结果（包含：前 100 条 + CSV 信息）
            # ----------------------------------------------------------------------
            resp = {
                "dataList": preview_records,
                "total": len(preview_records),
                "fileName": file_name,
                "filePath": file_path
            }

            return ResultEntityMethod.buildSuccessResult(data=resp)

        except Exception:
            logger.exception("[opc数据导出] - 本地数据导出未知异常")
            return ResultEntityMethod.buildFailedResult(message="本地数据导出失败")

    @staticmethod
    def data_preview(request: 'DataExportReq') -> ResultEntity:
        """
        [修改版] 根据筛选策略获取 ndjson 数据。
        不进行 CSV 导出，仅返回选定文件范围内的前 100 条数据用于预览。
        """
        try:
            # 1) dataType 处理
            data_type = getattr(request, "dataType", None) or "default"
            if data_type is None and isinstance(request, dict):
                data_type = request.get("dataType")
            if not data_type:
                data_type = "default"

            # 2) 解析 startDate / endDate（可能为空）
            start_raw = getattr(request, "startDate", None)
            end_raw = getattr(request, "endDate", None)
            if start_raw is None and isinstance(request, dict):
                start_raw = request.get("startDate")
            if end_raw is None and isinstance(request, dict):
                end_raw = request.get("endDate")

            start_dt = standardize_dt(parse_dt_maybe(start_raw))
            end_dt = standardize_dt(parse_dt_maybe(end_raw))
            logger.info("[data_preview] - 标准化时间窗口: start_dt=%s, end_dt=%s", start_dt, end_dt)

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

            try:
                records = query_by_time_range_with_pagination(data_type, start_ts, end_ts, 1, 100)
            except Exception as e:
                logger.exception("[opc数据预览 - SQLite] 查询失败: %s", e)
                return ResultEntityMethod.buildFailedResult(message="数据库查询失败")
            logger.info("[opc数据预览] - 获取数据成功 (返回 %d 条)",len(records))

            # 6) 返回结果 (移除 fileName 和 filePath)
            resp = {
                "dataList": records,
                "total": len(records),
            }
            return ResultEntityMethod.buildSuccessResult(data=resp)

        except Exception:
            logger.exception("[opc数据预览] - 数据获取未知异常")
            return ResultEntityMethod.buildFailedResult(message="数据获取失败")

    @staticmethod
    def qr_query(request: QrQueryReq) -> ResultEntity:
        try:
            qr_query_res = QrQueryRes(
                message=request['message'],
                type=request['type']
            )
            return ResultEntityMethod.buildSuccessResult(data=qr_query_res)
        except Exception as e:
            logger.exception("[opc qr扫描] - opc qr扫描未知失败", e)
            return ResultEntityMethod.buildFailedResult(message="opc qr扫描未知失败")

    @staticmethod
    def qr_export(request: QrExportReq) -> ResultEntity:
        try:

            #带自定义选项但无文本的二维码生成
            try:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_M,
                    box_size=request.get("size"),
                    border=request.get("border"),
                )
                data = request.to_qr_data()  # 返回过滤后的字典
                qr.add_data(data)
                qr.make(fit=True)

                # 创建 export 目录（如果不存在）
                export_dir = "export"
                if not os.path.exists(export_dir):
                    os.makedirs(export_dir)
                    logger.info(f"[qr 导出] - 创建目录: {export_dir}")

                def get_unique_filename(export_dir, filename):
                    """
                    生成唯一的文件名，如果存在相同文件名则自动递增数字
                    """
                    # 分离文件名和扩展名
                    name, ext = os.path.splitext(filename)
                    counter = 1
                    new_filename = filename
                    filepath = os.path.join(export_dir, new_filename)

                    # 检查文件是否存在，如果存在则递增数字
                    while os.path.exists(filepath):
                        new_filename = f"{name}_{counter}{ext}"
                        filepath = os.path.join(export_dir, new_filename)
                        counter += 1

                    return new_filename, filepath
                # 设置文件路径到 export 目录
                filename = request.get("filename")
                unique_filename, filepath = get_unique_filename(export_dir, filename)

                # img可导出返回
                img = qr.make_image(fill_color=request.get("fill_color"), back_color=request.get("back_color"))
                img.save(filepath)
                logger.info(f"[qr 导出] - 二维码已成功生成并保存为: {filepath}")
                logger.info(f"[qr 导出] - 编码的数据: {data}")
                qr_export_res = QrExportRes(
                    exportSuccess = True
                )
                return ResultEntityMethod.buildSuccessResult(data=qr_export_res)
            except Exception as e:
                logger.error("[qr 导出] - 生成二维码时出错:", e)
                return ResultEntityMethod.buildFailedResult(message="opc qr导出生成二维码出错")
        except Exception as e:
            logger.error("[qr 导出] - opc qr导出未知失败", e)
            return ResultEntityMethod.buildFailedResult(message="opc qr导出未知失败")

    @staticmethod
    def save(data_view: 'DataView') -> bool:
        try:
            record = data_view.to_dict()
            data_type = data_view.dataType
            if not data_type:
                data_type = "default"  # 可按需改默认

            # 3. 追加写入当日文件
            insert_one_record(data_type, record)

            logger.info("[opc数据存储] - 本地写入成功: %s", record.get("id"))
            return True

        # 由于 Manager 传入的已经是 DataView 实例，理论上不会有 ValidationError
        # 但保留更通用的 Exception 捕获
        except Exception as e:
            # 注意：这里我们移除了对 'ValidationError' 的专门捕获，
            # 因为数据在 Manager 线程中创建时就已经通过了 Pydantic 校验。
            # 如果需要，可以将 ValidationError 捕获合并到这个通用捕获块中。
            logger.error("[opc数据存储] - 写入文件未知失败: %s", e, exc_info=True)
            return False