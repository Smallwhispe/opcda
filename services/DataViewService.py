import logging
import os
from typing import Optional

import qrcode
import csv
import json

from models.DataView import DataView
from vo.ResultEntity import ResultEntity
from vo.QrExport import QrExportRes, QrExportReq
from vo.ResultEntity import ResultEntityMethod, ErrorCode
from vo.req import ModelPredictReq, DataExportReq, QrQueryReq
from vo.res import QrQueryRes

from datetime import datetime, date, timedelta

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

def list_available_files_for_type(dtype: str):
    """
    返回 (day(date), path) 列表，仅包含该 dataType 的合法 ndjson 文件，按日期升序。
    文件名格式：{dataType}_YYYY-MM-DD.ndjson
    """
    results = []
    if not os.path.exists(DATA_DIR):
        return results
    prefix = f"{dtype}_"
    for fn in os.listdir(DATA_DIR):
        if not fn.startswith(prefix) or not fn.endswith(EXT):
            continue
        # 期望形如 {dataType}_YYYY-MM-DD.ndjson
        date_part = fn[len(prefix):-len(EXT)]
        try:
            day = datetime.strptime(date_part, "%Y-%m-%d").date()
            results.append((day, os.path.join(DATA_DIR, fn)))
        except Exception:
            continue
    # 按日期升序
    results.sort(key=lambda x: x[0])
    return results

def files_in_range(d1: date, d2: date, available):
    """
    在 available[(day, path)] 中筛选 [d1, d2] 区间(含端点)的文件，保持 available 的升序顺序。
    """
    if d1 > d2:
        d1, d2 = d2, d1
    days_set = set()
    cur = d1
    while cur <= d2:
        days_set.add(cur)
        cur = cur + timedelta(days=1)
    return [(day, path) for (day, path) in available if day in days_set]

def find_nearest_available_day(target: date, available):
    """
    在按日期升序的 available=[(day(date), path), ...] 中，找到最接近 target 的一天。
    若有同样距离的前后两天，偏向较新的(靠后的)一天。
    返回: [(day, path)] 或 []（若 available 为空）
    """
    if not available:
        return []

    # 先检查是否恰好存在
    for d, p in available:
        if d == target:
            return [(d, p)]

    # 计算最小绝对间隔；间隔相同则选更晚的日期
    best = None      # (abs_diff, day, path)
    for d, p in available:
        diff = abs((d - target).days)
        if best is None:
            best = (diff, d, p)
        else:
            if diff < best[0]:
                best = (diff, d, p)
            elif diff == best[0] and d > best[1]:
                best = (diff, d, p)

    return [(best[1], best[2])] if best else []

class DataViewService:
    @staticmethod
    def dataExport(request: 'DataExportReq') -> ResultEntity:
        """
        将指定日期范围内(含端点)的 ndjson 合并写为单个 .csv 保存到 export 目录，并返回前100条作为 dataList。
        入参:
          - request.date: datetime(可空, 空则今天/Asia/Shanghai)
          - request.dataType: str(可空, 空则 'default')
        兜底策略:
          - 只给了一个日期: 导出该天；若该天无文件则就近选择最近有数据的一天
          - 两者都给但范围内无任何文件，或两者都没给: 导出“最新的”一个文件
        返回:
          - dataList: 前100条
          - total: len(dataList)
          - filePath: 导出的 csv 文件绝对路径
          - fileName: 导出的 csv 文件名
        """
        try:
            # 1) dataType
            data_type = getattr(request, "dataType", None)
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

            start_dt = parse_dt_maybe(start_raw)
            end_dt = parse_dt_maybe(end_raw)

            # 统一到本地时区
            if start_dt:
                start_dt = start_dt.astimezone(LOCAL_TZ) if start_dt.tzinfo else LOCAL_TZ.localize(start_dt)
            if end_dt:
                end_dt = end_dt.astimezone(LOCAL_TZ) if end_dt.tzinfo else LOCAL_TZ.localize(end_dt)

            # 3) 可用文件（该 dataType），按日期升序
            available = list_available_files_for_type(data_type)

            # 4) 依据入参选择文件
            selected_files = []  # [(day(date), path)]
            if start_dt and end_dt:
                selected_files = files_in_range(start_dt.date(), end_dt.date(), available)
            elif start_dt and not end_dt:
                target = start_dt.date()
                selected_files = [(d, p) for (d, p) in available if d == target]
                if not selected_files:
                    selected_files = find_nearest_available_day(target, available)
            elif end_dt and not start_dt:
                target = end_dt.date()
                selected_files = [(d, p) for (d, p) in available if d == target]
                if not selected_files:
                    selected_files = find_nearest_available_day(target, available)

            # 若未选中任何文件，退化到“最新的一个文件”
            if not selected_files:
                if available:
                    latest_day, latest_path = available[-1]
                    selected_files = [(latest_day, latest_path)]
                else:
                    logger.info("[opc数据导出] - 无可用数据文件: %s", DATA_DIR)
                    return ResultEntityMethod.buildFailedResult(
                        ErrorCode.NO_DATA.get_code(),
                        ErrorCode.NO_DATA.get_msg(),
                        None
                    )

            # 5) 读取 ndjson & 准备导出
            first_100 = []
            total_rows = 0
            columns = ["id", "temperature", "flow", "pressure", "concentration", "time"]

            # 6) 写 csv（合并全量）
            ensure_export_dir()

            # 组装导出文件名：单日 or 多日
            if len(selected_files) == 1:
                day_str = selected_files[0][0].isoformat()
                base_filename = f"{data_type}_{day_str}.csv"
            else:
                start_str = selected_files[0][0].isoformat()
                end_str = selected_files[-1][0].isoformat()
                base_filename = f"{data_type}_{start_str}_to_{end_str}.csv"

            out_path = os.path.join(EXPORT_DIR, base_filename)
            if os.path.exists(out_path):
                counter = 1
                name_only, ext = os.path.splitext(base_filename)
                while os.path.exists(out_path):
                    new_name = f"{name_only}_{counter}{ext}"
                    out_path = os.path.join(EXPORT_DIR, new_name)
                    counter += 1
            out_filename = os.path.basename(out_path)

            with open(out_path, "w", encoding="utf-8", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=columns)
                writer.writeheader()

                # 依日期升序合并
                for (day, src_path) in selected_files:
                    if not os.path.exists(src_path):
                        continue
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

            logger.info(
                "[opc数据导出] - 已导出为 csv: %s (共 %d 行，合并 %d 个文件)",
                out_path, total_rows, len(selected_files)
            )

            # 7) 返回“部分数据”（前100条）+ 导出文件信息
            resp = {
                "dataList": first_100,
                "total": len(first_100),
                "fileName": out_filename,
                "filePath": os.path.abspath(out_path),
            }
            return ResultEntityMethod.buildSuccessResult(data=resp)

        except Exception as e:
            logger.exception("[opc数据导出] - 本地数据导出未知异常: %s", e, exc_info=True)
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
            return ResultEntityMethod.buildFailedResult(message="模型调用失败")

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
                return ResultEntityMethod.buildFailedResult(message="opc qr导出生成二维码出错")
        except Exception as e:
            logger.error("[qr 导出] - opc qr导出未知失败", e)
            return ResultEntityMethod.buildFailedResult(message="opc qr导出未知失败")

    @staticmethod
    def save(data_view_instance: 'DataView') -> bool:
        """
        接收 Manager 线程传入的 DataView 实例，并将其持久化到本地文件。

        Args:
            data_view_instance: 已经从 OPC 原始数据转换好的 DataView 实例。
        """
        try:
            # ----------------------------------------------------
            # 移除所有 Flask Request 和 JSON 解析逻辑
            # 移除数据清洗和 Pydantic 实例化逻辑（因为数据已经实例化和清洗过）
            # ----------------------------------------------------

            # 1. 序列化为一行，时间为 'YYYY-MM-DD HH:MM:SS'
            # 直接使用传入的 DataView 实例
            record = data_view_instance.to_dict()

            # 2. 读取 dataType
            data_type = data_view_instance.dataType
            if not data_type:
                data_type = "default"  # 可按需改默认

            # 3. 追加写入当日文件
            # 假设 append_line 可以在该模块作用域内访问
            append_line(record, data_type)

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