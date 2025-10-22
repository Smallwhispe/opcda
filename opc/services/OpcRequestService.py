from vo import ResultEntity
from vo.req import DataCollectReq, ModelPredictReq, LimsQueryReq, DataExportReq


class OpcRequestService:
    @staticmethod
    def handleConnectRequest(request) -> ResultEntity:
        pass

    @staticmethod
    def handleBrowseRequest(request) -> ResultEntity:
        pass

    @staticmethod
    def handleSyncRead(request) -> ResultEntity:
        pass

    @staticmethod
    def handleSyncWrite(request) -> ResultEntity:
        pass

    @staticmethod
    def handleSubscribe(request) -> ResultEntity:
        pass

    @staticmethod
    def handleUnsubscribe(request) -> ResultEntity:
        pass

    @staticmethod
    def createOpcItemValue(request) -> ResultEntity:
        pass

    @staticmethod
    def handleWriteOperation(request) -> ResultEntity:
        pass

    @staticmethod
    def getActiveClients(request) -> ResultEntity:
        pass