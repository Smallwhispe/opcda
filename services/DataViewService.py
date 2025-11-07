import logging
import os
import qrcode
from pydantic import ValidationError

from models.DataView import db, DataView
from vo import ResultEntity
from vo.QrExport import QrExportRes, QrExportReq
from vo.ResultEntity import ResultEntityMethod, ErrorCode
from vo.req import DataCollectReq, ModelPredictReq, DataExportReq, QrQueryReq
from vo.res import QrQueryRes

logger = logging.getLogger()
class DataViewService:
    @staticmethod
    def dataCollect(request: DataCollectReq) -> ResultEntity:
        try:
            links = DataView.query.all()
            # .filter
            print(links)
            # 将查询结果转换为字典列表
            dataCollectRes = {'dataList': links, 'total': len(links)}
            return ResultEntityMethod.buildSuccessResult(data=dataCollectRes)
        except Exception as e:
            logger.error("[opc数据导出] - opc数据导出未知异常", e)

    @staticmethod
    def dataCollectByPage(request: DataCollectReq) -> ResultEntity:
        try:
            # 如果有分页参数，进行验证
            page = getattr(request, 'page', 1)
            page_size = getattr(request, 'size', 100)

            if page < 1:
                page = 1
            if page_size < 1 or page_size > 1000:  # 限制最大页大小
                page_size = 100

            logger.info(f"[opc分页] - 处理数据展示请求 - 页码: {page}, 页大小: {page_size}")

            try:
                query = DataView.query

                # 可以添加过滤条件（根据request中的参数）
                # if hasattr(request, 'start_time') and request.start_time:
                #     query = query.filter(DataView.time >= request.start_time)
                # if hasattr(request, 'end_time') and request.end_time:
                #     query = query.filter(DataView.time <= request.end_time)
                #使用分页（推荐用于大量数据）
                pagination = query.paginate(
                    page=page,
                    per_page=page_size,
                    error_out=False
                )
                links = pagination.items
                #total为符合查询总数量
                total = pagination.total

            except Exception as db_error:
                logger.error(f"[opc分页] - 数据库查询失败: {str(db_error)}", exc_info=True)
                return ResultEntityMethod.buildFailedResult(message="数据库服务暂时不可用")

            # 3. 数据验证和处理
            if not links:
                logger.info("[opc分页] - 未查询到符合条件的数据")
                return ResultEntityMethod.buildSuccessResult(ErrorCode.NO_DATA.get_code(),ErrorCode.NO_DATA.get_msg(),None)

            try:
                # 构建响应数据
                dataExportRes = {'dataList': links,'total': len(links)}

                # 记录成功日志
                logger.info(f"[opc分页] - 数据分页查询请求处理成功，返回 {len(links)} 条数据")

                return ResultEntityMethod.buildSuccessResult(data=dataExportRes)

            except Exception as processing_error:
                logger.error(f"[opc分页] - 数据处理过程中发生错误: {str(processing_error)}", exc_info=True)
                return ResultEntityMethod.buildFailedResult(message="数据处理失败，请稍后重试")

        except Exception as e:
            # 全局异常捕获
            logger.critical(f"[opc分页] - 数据导出处理发生严重错误: {str(e)}", exc_info=True)
            return ResultEntityMethod.buildFailedResult(message="系统内部错误，请联系管理员")

    @staticmethod
    def dataExport(request: DataExportReq) -> ResultEntity:
        try:
            links = DataView.query.all()
            #.filter
            print(links)
            # 将查询结果转换为字典列表
            dataExportRes = {'dataList': links, 'total': len(links)}
            return ResultEntityMethod.buildSuccessResult(data=dataExportRes)
        except Exception as e:
            logger.error("[opc数据导出] - opc数据导出未知异常", e)

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
            if not request.args:
                logger.error("[opc数据存储] - opc数据存储未检测到请求")
                return False
            data = request.get_json()
            if not data:
                logger.error("[opc数据存储] - opc数据存储data为空")
                return False
            dataView = DataView.model_validate(data)

            db.session.add(dataView)
            db.session.commit()
            return True
        except ValidationError as e:
            logger.error("[opc数据存储] - opc数据存储参数不正常", e)
            return False
        except Exception as e:
            logger.error("[opc数据存储] - opc数据存储未知失败", e)
            return False
