import logging

from pydantic import ValidationError

from models.DataView import db, DataView
from vo import ResultEntity
from vo.req import DataCollectReq, ModelPredictReq, LimsQueryReq, DataExportReq

logger = logging.getLogger()
class DataViewService:
    @staticmethod
    def dataCollect(request: DataCollectReq) -> ResultEntity:
        pass

    @staticmethod
    def dataCollectByPage(request: DataCollectReq) -> ResultEntity:
        pass

    @staticmethod
    def dataExport(request: DataExportReq) -> ResultEntity:
        pass

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
