from typing import Optional

from pydantic import BaseModel

class QrExportRes(BaseModel):
    exportSuccess: bool = False

class QrExportReq(BaseModel):

    def to_qr_data(self):
        # 排除特定字段后返回字典
        exclude_fields = {'filename', 'size', 'border', 'fill_color', 'back_color'}
        data_dict = self.dict(exclude=exclude_fields)
        # 删除值为 None 的项
        return {k: v for k, v in data_dict.items() if v is not None}

    filename: Optional[str] = "example.jpg"
    size: Optional[int] = 4
    border: Optional[int] = 4
    fill_color: Optional[str] = "black"
    back_color: Optional[str] = "white"
    # 取样日期
    sampled_date: Optional[str] = None
    # 取样点
    sampling_point: Optional[str] = None
    # 名称
    name: Optional[str] = None
    # 单位显示
    units_display: Optional[str] = None
    # 格式化输入
    formatted_entry: Optional[str] = None
    # 取样时间
    drawtime: Optional[str] = None