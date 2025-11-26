import logging
from datetime import datetime
from typing import Optional, Any, Dict
from uuid import uuid4
import re
import pytz
from pydantic import BaseModel, Field

LOCAL_TZ = pytz.timezone("Asia/Shanghai")
logger = logging.getLogger(__name__)

def now_jst() -> datetime:
    # 生成带时区的当前时间（pytz 的推荐写法）
    return LOCAL_TZ.localize(datetime.now())


class DataView(BaseModel):
    id: Optional[int] = None
    dataType: Optional[str] = None
    temperature: Optional[str] = None
    flow: Optional[str] = None
    pressure: Optional[str] = None
    concentration: Optional[str] = None
    quality: Optional[bool] = False
    # 确保 time 字段存储的是带时区的 datetime 对象
    time: datetime = Field(default_factory=now_jst)

    def __repr__(self):
        return (f"DataView(id='{self.id}', "
                f"dataType='{self.dataType}', "
                f"temperature='{self.temperature}', "
                f"flow='{self.flow}', "
                f"pressure={self.pressure}, "
                f"concentration={self.concentration}, "
                f"quality={self.quality}, "
                f"time={self.time}, )")

    def to_dict(self):

        # -----------------------------------------------------------------
        # !!! 核心修复代码：在转换字符串前，将时间对象转换为 LOCAL_TZ (Asia/Shanghai) 时区 !!!
        # -----------------------------------------------------------------
        # 1. 确保时间字段有 tzinfo，并转换到本地时区 (CST)
        if self.time.tzinfo is None:
            # 如果是无时区时间，先假设它是本地时间并加上时区信息
            local_time = LOCAL_TZ.localize(self.time)
        else:
            # 如果是带时区时间 (如 UTC)，则将其转换为本地时区
            local_time = self.time.astimezone(LOCAL_TZ)

        # 2. 使用本地时区的对象进行格式化
        time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")
        time_str_final = f"{time_str}+08:00"
        return {
            'id': self.id,
            'dataType': self.dataType,
            'temperature': self.temperature,
            'flow': self.flow,
            'pressure': self.pressure,
            'concentration': self.concentration,
            'quality': self.quality,
            'time': time_str_final  # 使用本地时区格式化的字符串
        }


# --- 其他辅助函数和转换函数保持不变 ---

# 建立一个关键词到DataView字段的映射
OPC_FIELD_MAP = {
    'Real8': 'temperature',  # 假设 Real8 映射到 temperature
    'Real4': 'flow',  # 假设 Real4 映射到 flow
    'Int4': 'pressure',  # 假设 Int4 映射到 pressure
    'String': 'concentration'  # 假设 String 映射到 concentration
}


# clean_opc_string 函数保持不变...
def clean_opc_string(tag_name: str, raw_value: Any) -> Optional[str]:
    """
    根据数据类型清理和格式化值，全部转为字符串。
    专门用于处理浓度字符串，去除单位。
    """
    if raw_value is None:
        return None

    # 针对 String 类型（浓度）的特殊处理：提取数字部分
    if 'String' in tag_name:
        # 正则表达式匹配开头处的数字、小数点或逗号，去除单位 (如 '0.4980 wt%')
        match = re.search(r"^\s*([\d\.\,]+)", str(raw_value).strip())
        return match.group(1) if match else str(raw_value).strip()

    # 对于数字和布尔值，直接转换为字符串
    return str(raw_value)


# parse_opc_data_to_data_view 函数保持不变...
def parse_opc_data_to_data_view(opc_raw_data: Dict[str, Dict[str, Any]], data_type_tag: str = "default") -> DataView:
    """
    将OPC原始数据（嵌套字典）转换为DataView实例。
    (已修复错误的时区标签)
    """

    payload: Dict[str, Any] = {
        'dataType': data_type_tag,
        'quality': True
    }
    first_timestamp = None

    for tag_name, tag_data in opc_raw_data.items():

        value = tag_data.get('value')
        quality_str = tag_data.get('quality', 'Bad')
        timestamp_str = tag_data.get('timestamp')

        # 提取时间戳（取第一个有效的时间戳作为记录时间）
        if timestamp_str and not first_timestamp:

            # ----------------------------------------------------
            # !!! 时区修正逻辑开始 !!!
            # ----------------------------------------------------

            # 1. 查找时区偏移量的分隔符 (+ 或 -)
            # (从第11个字符开始查找，以避免误判日期中的 -)
            tz_split = -1
            if '+' in timestamp_str[10:]:
                tz_split = timestamp_str.rfind('+')
            elif '-' in timestamp_str[10:]:
                tz_split = timestamp_str.rfind('-')

            # 2. 剥离错误的时区标签，只获取时间部分
            time_part = timestamp_str
            if tz_split != -1:
                time_part = timestamp_str[:tz_split]  # 获取 '2025-11-10 16:47:01.476000'

            # 3. 将字符串解析为“纯净 (naive)”的 datetime 对象
            #    (必须处理 .%f 微秒，同时兼容 Python 3.6 的 strptime)
            dt_naive = None
            try:
                dt_naive = datetime.strptime(time_part, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                # 如果没有微秒，则回退到不带微秒的格式
                dt_naive = datetime.strptime(time_part, "%Y-%m-%d %H:%M:%S")

            # 4. 强制将这个“纯净”时间标记为 LOCAL_TZ (Asia/Shanghai)
            first_timestamp = LOCAL_TZ.localize(dt_naive)

        if quality_str != 'Good':
            payload['quality'] = False

        mapped_field = None
        for key, field in OPC_FIELD_MAP.items():
            if key in tag_name:
                mapped_field = field
                break

        if mapped_field:
            payload[mapped_field] = clean_opc_string(tag_name, value)

    # 赋值时间戳
    if first_timestamp:
        payload['time'] = first_timestamp
    else:
        # 如果 OPC 数据没有时间戳，使用 now_jst() 作为备用
        payload['time'] = now_jst()

    return DataView(**payload)