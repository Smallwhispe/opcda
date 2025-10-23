from dataclasses import dataclass
from typing import Optional, List

from pydantic import BaseModel

from models.DataView import DataView


@dataclass
class DataCollectRes(BaseModel):
    """数据展示响应"""
    #数据条目数量
    total: Optional[int] = None
    #工艺数据展示
    dataList: Optional[List[DataView]] = None

@dataclass
class DataExportRes(BaseModel):
    """数据导出响应"""
    #数据条目数量
    total: Optional[int] = None
    #工艺数据展示
    dataList: Optional[List[DataView]] = None

@dataclass
class LimsQueryRes(BaseModel):
    """LIMS查询响应"""
    #TODO 二维码查询

class Product:
    #粗汽油干点
    tough: Optional[str] = None
    #稳定汽油干点
    stable: Optional[str] = None
    #稳定汽油蒸汽压
    pressure: Optional[str] = None


@dataclass
class ModelPredictRes(BaseModel):
    """模型预测响应"""
    #模型版本号
    version: Optional[str] = None
    #模型预测起始时间
    startTime: Optional[int] = None
    #模型预测截止时间
    endTime: Optional[int] = None
    #工艺参数
    produce: Optional[Product] = None
    # 添加这行配置
    model_config = {
        "arbitrary_types_allowed": True
    }