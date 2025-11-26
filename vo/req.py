from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class DataCollectReq(BaseModel):
    """数据展示请求"""
    #页数
    page: Optional[int] = None
    #每页数量
    size: Optional[int] = None
    #数据类型
    dataType: Optional[str] = None
    #起始时间
    startTime: Optional[datetime] = None
    #截止时间
    endTime: Optional[datetime] = None

class DataExportReq(BaseModel):
    """数据导出请求"""
    #起始时间
    startDate: Optional[datetime] = None
    #结束时间
    endDate: Optional[datetime] = None
    #数据类型
    dataType: Optional[str] = None

class QrQueryReq(BaseModel):
    message: Optional[str] = None
    type: Optional[str] = None

class Produce:
    arg2_ti1352_pv: Optional[str] = None
    arg2_ti1329_pv: Optional[str] = None
    arg2_ti1328_pv: Optional[str] = None
    arg2_pic1306_pv: Optional[str] = None
    arg2_ti1338_pv: Optional[str] = None
    arg2_fic1308_pv: Optional[str] = None
    arg2_fic1309_pv: Optional[str] = None
    arg2_fic1310_pv: Optional[str] = None
    arg2_fic1303_pv: Optional[str] = None
    arg2_fic1311_pv: Optional[str] = None
    arg2_ti1330_pv: Optional[str] = None


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