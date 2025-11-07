from typing import Optional, Any

from pydantic import BaseModel


class DataCollectReq(BaseModel):
    """数据展示请求"""
    #页数
    page: Optional[int] = None
    #每页数量
    size: Optional[int] = None
    #起始时间
    startTime: Optional[int] = None
    #截止时间
    endTime: Optional[int] = None

class DataExportReq(BaseModel):
    """数据导出请求"""
    #起始时间
    startTime: Optional[int] = None
    #截止时间
    endTime: Optional[int] = None

class QrQueryReq(BaseModel):
    message: Optional[str] = None
    type: Optional[str] = None

class Produce:
    #分馏塔顶温度
    temperature: Optional[str] = None
    #分馏塔顶压力
    pressure: Optional[str] = None
    #粗汽油流量
    liquid: Optional[str] = None


class ModelPredictReq(BaseModel):
    """模型预测请求"""
    #模型版本号
    version: Optional[str] = None
    #模型预测起始时间
    startTime: Optional[int] = None
    #模型预测截止时间
    endTime: Optional[int] = None
    #工艺参数
    produce: Optional[Produce] = None
    # 添加这行配置, 允许嵌套的produce不是默认类型的存在
    model_config = {
        "arbitrary_types_allowed": True
    }