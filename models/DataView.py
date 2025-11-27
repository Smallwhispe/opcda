from datetime import datetime
from typing import Optional, Any, Dict, List, Union
from uuid import uuid4
import re
import pytz
from pydantic import BaseModel, Field

LOCAL_TZ = pytz.timezone("Asia/Shanghai")


def now_jst() -> datetime:
    return LOCAL_TZ.localize(datetime.now())


# ==========================================
# 1. 更新 DataView 模型
# ==========================================
class DataView(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    dataType: Optional[str] = None

    # 存储每个 Tag 的具体质量 (Key: 完整Tag名, Value: Good/Bad)
    qualities: Dict[str, str] = Field(default_factory=dict)

    # --- 9 个具体 DCS 点位的数值字段 ---
    tic1201b: Optional[Any] = None
    tic1345: Optional[Any] = None
    ti1306: Optional[Any] = None
    ti1329: Optional[Any] = None
    ti1352a: Optional[Any] = None

    fic1303: Optional[Any] = None
    fic1309: Optional[Any] = None
    fi1314: Optional[Any] = None

    pic1302: Optional[Any] = None

    # 时间字段
    time: datetime = Field(default_factory=now_jst)

    def to_dict(self):
        """
        转换为前端和数据库都需要的嵌套字典格式：
        {
            "id": "...",
            "time": "...",
            "TIC1201B.PIDA.PV": { "value": 123.4, "quality": "Good" },
            ...
        }
        """
        # 1. 时区处理
        if self.time.tzinfo is None:
            local_time = LOCAL_TZ.localize(self.time)
        else:
            local_time = self.time.astimezone(LOCAL_TZ)

        time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")
        time_str_final = f"{time_str}+08:00"

        # 2. 辅助组装函数
        def make_item(field_val, tag_name):
            # 获取质量，默认为 Bad
            qual = self.qualities.get(tag_name, 'Bad')

            # 如果有数值但没记录质量（防御性逻辑），默认视为 Good
            if field_val is not None and tag_name not in self.qualities:
                qual = 'Good'

            return {
                'value': field_val,
                'quality': qual
            }

        # 3. 返回结构化数据
        return {
            'id': self.id,
            'dataType': self.dataType,
            'time': time_str_final,

            # --- 映射回完整 Tag Name ---
            'TIC1201B.PIDA.PV': make_item(self.tic1201b, 'TIC1201B.PIDA.PV'),
            'TIC1345.PIDA.PV': make_item(self.tic1345, 'TIC1345.PIDA.PV'),
            'TI1306.DACA.PV': make_item(self.ti1306, 'TI1306.DACA.PV'),
            'TI1329.DACA.PV': make_item(self.ti1329, 'TI1329.DACA.PV'),
            'TI1352A.DACA.PV': make_item(self.ti1352a, 'TI1352A.DACA.PV'),

            'FIC1303.PIDA.PV': make_item(self.fic1303, 'FIC1303.PIDA.PV'),
            'FIC1309.PIDA.PV': make_item(self.fic1309, 'FIC1309.PIDA.PV'),
            'FI1314.DACA.PV': make_item(self.fi1314, 'FI1314.DACA.PV'),

            'PIC1302.PIDA.PV': make_item(self.pic1302, 'PIC1302.PIDA.PV'),
        }


# ==========================================
# 2. 映射配置
# Key: Tag 中的关键特征串, Value: DataView 属性名
# ==========================================
OPC_FIELD_MAP = {
    'TIC1201B': 'tic1201b',
    'TIC1345': 'tic1345',
    'TI1306': 'ti1306',
    'TI1329': 'ti1329',
    'TI1352A': 'ti1352a',
    'FIC1303': 'fic1303',
    'FIC1309': 'fic1309',
    'FI1314': 'fi1314',
    'PIC1302': 'pic1302'
}


def clean_opc_value(val: Any) -> Any:
    """清理数值，尝试转为 float，如果带单位则提取数字"""
    if val is None:
        return None
    try:
        # 直接尝试转换
        return float(val)
    except (ValueError, TypeError):
        # 处理字符串 "123.45 kg/h"
        s_val = str(val).strip()
        match = re.search(r"^(-?\d+(\.\d+)?)", s_val)
        if match:
            return float(match.group(1))
    return val


# ==========================================
# 3. 解析逻辑 (适配 List 输入)
# ==========================================
def parse_opc_data_to_data_view(opc_raw_data: Union[List[tuple], Dict], data_type_tag: str = "default") -> DataView:
    """
    将OPC原始数据转换为DataView实例。
    支持输入格式：
    [('Tag', Val, Qual, Time), ...]
    """

    model_data: Dict[str, Any] = {
        'dataType': data_type_tag,
        'qualities': {}
    }
    first_timestamp = None

    # --- 1. 统一转为可遍历的 (tag, val, qual, time) 列表 ---
    items_to_process = []

    if isinstance(opc_raw_data, list):
        # 适配你提供的: [('TIC...', 1.2, 'Good', 'Time'), ...]
        items_to_process = opc_raw_data
    elif isinstance(opc_raw_data, dict):
        # 兼容旧格式字典
        for k, v in opc_raw_data.items():
            items_to_process.append((k, v.get('value'), v.get('quality'), v.get('timestamp')))

    # --- 2. 遍历处理数据 ---
    for item in items_to_process:
        if len(item) < 4: continue

        tag_name, raw_val, raw_qual, ts_str = item[:4]

        # A. 解析时间 (只取第一个非空的)
        if ts_str and not first_timestamp:
            try:
                # 处理可能带有的 +00:00 时区后缀
                clean_ts_str = str(ts_str)
                if '+' in clean_ts_str:
                    clean_ts_str = clean_ts_str.split('+')[0]
                elif clean_ts_str.count('-') > 2:  # 处理 2025-11-27... 中的负号
                    last_dash = clean_ts_str.rfind('-')
                    if last_dash > 10:  # 确保不是日期的横杠
                        clean_ts_str = clean_ts_str[:last_dash]

                dt_naive = datetime.strptime(clean_ts_str.strip(), "%Y-%m-%d %H:%M:%S.%f")
                first_timestamp = LOCAL_TZ.localize(dt_naive)
            except (ValueError, TypeError):
                # 如果解析失败，暂不处理，后面兜底
                pass

        # B. 记录质量
        # 统一转为 'Good' 或 'Bad'
        is_good = str(raw_qual).upper() in ['GOOD', 'TRUE', '1']
        model_data['qualities'][tag_name] = 'Good' if is_good else 'Bad'

        # C. 映射数值到 DataView 字段
        mapped_field = None
        for key, field in OPC_FIELD_MAP.items():
            if key in tag_name:
                mapped_field = field
                break

        if mapped_field:
            model_data[mapped_field] = clean_opc_value(raw_val)

    # --- 3. 兜底时间 ---
    if first_timestamp:
        model_data['time'] = first_timestamp
    else:
        model_data['time'] = now_jst()

    return DataView(**model_data)