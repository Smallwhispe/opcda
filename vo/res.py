from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from models.DataView import DataView

class DataCollectRes(BaseModel):
    """数据展示响应"""
    #数据条目数量
    #分页即为当前页数量
    total: Optional[int] = None
    #工艺数据展示
    dataList: Optional[List[DataView]] = None

class DataExportRes(BaseModel):
    """数据导出响应"""

    #数据文件名称
    fileName: Optional[str] = None
    #数据文件路径
    filePath: Optional[str] = None

class QrQueryRes(BaseModel):
    message: Optional[str] = None
    type: Optional[str] = None

class Product:
    #粗汽油干点
    tough: Optional[str] = None
    #稳定汽油干点
    stable: Optional[str] = None
    #稳定汽油蒸汽压
    pressure: Optional[str] = None

class ModelPredictRes(BaseModel):
    """模型预测响应"""
    #模型版本号
    version: Optional[str] = None
    #模型预测起始时间
    startTime: Optional[int] = None
    #模型预测截止时间
    endTime: Optional[int] = None
    #模型预测时间
    time: Optional[datetime] = None
    #工艺参数
    result: Optional[Dict[str, Any]] = None

class PredictResultRes(BaseModel):
    """数据展示响应"""
    #数据条目数量
    #分页即为当前页数量
    total: Optional[int] = None
    #工艺数据展示
    dataList: Optional[List[Dict[str, Any]]] = None