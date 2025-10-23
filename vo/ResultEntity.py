from dataclasses import dataclass
from typing import Generic, TypeVar, Optional, Any
from enum import Enum, unique

T = TypeVar('T')  # 泛型类型参数

@dataclass
class ResultEntity(Generic[T]):

    def __init__(self, success: bool, code: str, message: str, data: Optional[T] = None):
        self.success = success
        self.code = code
        self.message = message
        self.data = data

    """统一响应结果实体"""
    code: str  # 状态码
    message: str  # 消息
    data: Optional[T] = None  # 数据（泛型）
    success: bool = False  # 是否成功

    ##初始化后可以进行的操作
    # def __post_init__(self):
    #     if self.timestamp is None:
    #         import time
    #         self.timestamp = int(time.time())
    #     if self.code == 200:
    #         self.success = True

@unique  # 确保值唯一
class ErrorCode(Enum):
    """错误码枚举"""
    SUCCESS = ("000000", "成功")
    FAILURE = ("999999", "失败")
    LINK_SUCCESS = ("000001", "连接成功")
    LINK_FAILURE = ("000002", "连接失败")
    UNLINK_SUCCESS = ("000003", "断连成功")
    UNLINK_FAILURE = ("000004", "断连失败")
    VALID_FAILURE = ("000005", "参数验证失败")
    NO_PARAM = ("000006", "无参数")
    SERVICE_FAILURE = ("000007", "服务调用失败")
    NO_REQUEST = ("000008", "没有请求体")
    NO_DATA = ("000009", "未找到相关数据")

    def __init__(self, code: str, msg: str):
        self._code = code
        self._msg = msg

    def get_code(self) -> str:
        return self._code

    def get_msg(self) -> str:
        return self._msg

    @classmethod
    def from_code(cls, code: str) -> Optional['ErrorCode']:
        """根据code获取枚举"""
        for error_code in cls:
            if error_code.get_code() == code:
                return error_code
        return None

class ResultEntityMethod:
    """结果构建工具类"""

    @staticmethod
    def buildSuccessResult(code: str = "000000", message: str = "成功", data: Any = None) -> ResultEntity[T]:
        """构建成功结果"""
        return ResultEntity(
            success=True,
            code=code,
            message=message,
            data=data
        )

    @staticmethod
    def buildFailedResult(code: str = "999999", message: str = "失败", data: Any = None) -> ResultEntity[Any]:
        """构建错误结果"""
        return ResultEntity(
            success=False,
            code=code,
            message=message,
            data=data
        )