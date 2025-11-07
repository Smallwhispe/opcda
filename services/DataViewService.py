import logging
import os
from typing import Optional

import qrcode
import csv
import json
from pydantic import ValidationError

from models.DataView import DataView
from vo import ResultEntity
from vo.QrExport import QrExportRes, QrExportReq
from vo.ResultEntity import ResultEntityMethod, ErrorCode
from vo.req import ModelPredictReq, DataExportReq, QrQueryReq
from vo.res import QrQueryRes

from datetime import datetime, date

import pytz
logger = logging.getLogger()
LOCAL_TZ = pytz.timezone("Asia/Shanghai")

DATA_DIR = "repository"
EXT = ".ndjson"
EXPORT_DIR = "export"

def ensure_export_dir():
    if not os.path.exists(EXPORT_DIR):
        os.makedirs(EXPORT_DIR)

def date_to_fname(d: date, data_type: str) -> str:
    """data/<dataType>_YYYY-MM-DD.ndjson"""
    ensure_export_dir()
    fname = "{}_{}{}".format(data_type, d.isoformat(), EXT)
    return os.path.join(DATA_DIR, fname)

def today_file_path(data_type: str) -> str:
    """按本地时区(Asia/Shanghai)的日期命名文件"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    day = datetime.now(LOCAL_TZ).date().isoformat()  # e.g. '2025-11-07'
    return os.path.join(DATA_DIR, data_type +'_'+ day + EXT)

def append_line(d: dict, data_type: str):
    """将一条字典记录以一行 JSON 追加写入当天文件"""
    path = today_file_path(data_type)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(d, ensure_ascii=False))
        f.write("\n")

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



class DataViewService:
    @staticmethod
    def dataExport(request: 'DataExportReq') -> ResultEntity:
        """
        将当天 ndjson 全量写为 .xls 保存到 export 目录，并返回前100条作为 dataList。
        入参:
          - request.date: datetime(可空, 空则今天/Asia/Shanghai)
          - request.dataType: str(可空, 空则 'default')
        返回:
          - dataList: 前100条
          - total: len(dataList)（当前页数量）
          - filePath: 导出的 xls 文件绝对路径
          - fileName: 导出的 xls 文件名
        """
        try:
            # 1) dataType
            data_type = getattr(request, "dataType", None)
            if data_type is None and isinstance(request, dict):
                data_type = request.get("dataType")
            if not data_type:
                data_type = "default"

            # 2) date（默认今天）
            date_raw = getattr(request, "date", None)
            if date_raw is None and isinstance(request, dict):
                date_raw = request.get("date")

            dt = parse_dt_maybe(date_raw)
            if dt is None:
                dt = datetime.now(LOCAL_TZ)
            else:
                dt = dt.astimezone(LOCAL_TZ) if dt.tzinfo else LOCAL_TZ.localize(dt)

            day = dt.date()

            # 3) 源文件路径
            src_path = date_to_fname(day, data_type)   # 注意这里是 _date_to_fname
            if not os.path.exists(src_path):
                logger.info("[opc数据导出] - 当天文件不存在: %s", src_path)
                # 按你们之前习惯：用 SuccessResult 返回 NO_DATA 编码与信息
                return ResultEntityMethod.buildFailedResult(
                    ErrorCode.NO_DATA.get_code(),
                    ErrorCode.NO_DATA.get_msg(),
                    None
                )

            # 4) 读取 ndjson & 准备导出
            first_100 = []
            total_rows = 0
            columns = ["id", "temperature", "flow", "pressure", "concentration", "time"]

            # 5) 写 csv（全量）
            ensure_export_dir()
            base_filename = "{}_{}.csv".format(data_type, day.isoformat())
            out_path = os.path.join(EXPORT_DIR, base_filename)
            if os.path.exists(out_path):
                counter = 1
                name_only, ext = os.path.splitext(base_filename)
                while os.path.exists(out_path):
                    new_name = "{}_{}{}".format(name_only, counter, ext)
                    out_path = os.path.join(EXPORT_DIR, new_name)
                    counter += 1
            out_filename = os.path.basename(out_path)

            with open(out_path, "w", encoding="utf-8", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=columns)
                writer.writeheader()

                with open(src_path, "r", encoding="utf-8") as f:
                    for line in f:
                        s = line.strip()
                        if not s:
                            continue
                        try:
                            obj = json.loads(s)
                        except Exception:
                            continue

                        if len(first_100) < 100:
                            first_100.append(obj)

                        row = {col: obj.get(col, "") for col in columns}
                        writer.writerow(row)
                        total_rows += 1

            logger.info("[opc数据导出] - 已导出为 csv: %s (共 %d 行)", out_path, total_rows)

            # 6) 返回“部分数据”（前100条）+ 导出文件信息
            resp = {
                "dataList": first_100,
                "total": len(first_100),     # 当前页数量（前100条）
                "fileName": out_filename,
                "filePath": os.path.abspath(out_path),
            }
            return ResultEntityMethod.buildSuccessResult(data=resp)

        except Exception as e:
            logger.error("[opc数据导出] - 本地数据导出未知异常: %s", e, exc_info=True)
            return ResultEntityMethod.buildFailedResult(message="本地数据导出失败")

    @staticmethod
    def modelPredict(request: ModelPredictReq, modelPredictService=None) -> ResultEntity:
        try:
            ##TODO这里应该是调用师姐的模型预测模块函数
            result = modelPredictService.modelPredict(request)
            # 将查询结果转换为字典列表
            modelPredictRes = {'version': result.version, 'startTime': result.startTime, 'endTime': result.endTime, 'produce': result.produce}
            return ResultEntityMethod.buildSuccessResult(data=modelPredictRes)
        except Exception as e:
            logger.error("[opc数据导出] - opc数据导出未知异常", e)

    @staticmethod
    def qrQuery(request: QrQueryReq) -> ResultEntity:
        try:
            qrQueryRes = QrQueryRes(
                message=request['message'],
                type=request['type']
            )
            return ResultEntityMethod.buildSuccessResult(data=qrQueryRes)
        except Exception as e:
            logger.error("[opc qr扫描] - opc qr扫描未知失败", e)
            return ResultEntityMethod.buildFailedResult(message="opc qr扫描未知失败")

    @staticmethod
    def qrExport(request: QrExportReq) -> ResultEntity:
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
                qrExportRes = QrExportRes(
                    exportSuccess = True
                )
                return ResultEntityMethod.buildSuccessResult(data=qrExportRes)
            except Exception as e:
                logger.error("[qr 导出] - 生成二维码时出错:", e)
                ResultEntityMethod.buildFailedResult(message="opc qr导出生成二维码出错")
        except Exception as e:
            logger.error("[qr 导出] - opc qr导出未知失败", e)
            return ResultEntityMethod.buildFailedResult(message="opc qr导出未知失败")

    @staticmethod
    def save(request) -> bool:
        try:
            # 对于 Flask：args 为空并不代表无效请求，这里仅做温和检查
            data = request.get_json(silent=True) or {}
            if not data:
                logger.error("[opc数据存储] - 请求体为空或非 JSON")
                return False

            # 只接收业务字段，id/time 由模型 default_factory 自动生成
            allowed = {"dataType", "temperature", "flow", "pressure", "concentration", "quality"}
            payload = {k: v for k, v in data.items() if k in allowed}

            # Pydantic v1：用 parse_obj（或 DataView(**payload) 也可以）
            data_view = DataView(**payload)

            # 序列化为一行，时间为 'YYYY-MM-DD HH:MM:SS'
            record = data_view.to_dict()

            # 读取 dataType
            data_type = data_view.dataType
            if not data_type:
                data_type = "default"  # 可按需改默认
            # 追加写入当日文件
            append_line(record, data_type)

            logger.info("[opc数据存储] - 本地写入成功: %s", record.get("id"))
            return True

        except ValidationError as e:
            logger.error("[opc数据存储] - 参数校验失败: %s", e, exc_info=True)
            return False
        except Exception as e:
            logger.error("[opc数据存储] - 未知失败: %s", e, exc_info=True)
            return False