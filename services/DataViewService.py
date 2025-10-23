import logging

from pydantic import ValidationError

from models.DataView import db, DataView
from vo import ResultEntity
from vo.ResultEntity import ResultEntityMethod, ErrorCode
from vo.req import DataCollectReq, ModelPredictReq, LimsQueryReq, DataExportReq

logger = logging.getLogger()
class DataViewService:
    @staticmethod
    def dataCollect(request: DataCollectReq) -> ResultEntity:
        try:
            # 定义一个函数，用于处理对`/linklist`路由的GET请求。
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
                total = pagination.total

            except Exception as db_error:
                logger.error(f"数据库查询失败: {str(db_error)}", exc_info=True)
                return ResultEntityMethod.buildFailedResult(message="数据库服务暂时不可用")

            # 3. 数据验证和处理
            if not links:
                logger.info("[opc分页] - 未查询到符合条件的数据")
                return ResultEntityMethod.buildSuccessResult(ErrorCode.NO_DATA.get_code(),ErrorCode.NO_DATA.get_msg(),None)

            try:
                # 构建响应数据
                dataExportRes = {'dataList': links,'total': total}

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
            # 定义一个函数，用于处理对`/linklist`路由的GET请求。
            links = DataView.query.all()
            #.filter
            print(links)
            # 将查询结果转换为字典列表
            dataExportRes = {'dataList': links, 'total': len(links)}
            return ResultEntityMethod.buildSuccessResult(data=dataExportRes)
        except Exception as e:
            logger.error("[opc数据导出] - opc数据导出未知异常", e)

    @staticmethod
    def modelPredict(request: ModelPredictReq) -> ResultEntity:
        pass

    @staticmethod
    def limsQuery(request: LimsQueryReq) -> ResultEntity:
        pass

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
