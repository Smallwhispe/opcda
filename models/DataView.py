import logging
from datetime import datetime
from typing import Optional, Any, Dict, List, Union
from uuid import uuid4
import re
import pytz
from pydantic import BaseModel, Field

LOCAL_TZ = pytz.timezone("Asia/Shanghai")
logger = logging.getLogger(__name__)

def now_jst() -> datetime:
    return LOCAL_TZ.localize(datetime.now())


# ==========================================
# 1. 更新 DataView 模型
# ==========================================
class DataView(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    dataType: Optional[str] = None

    # 存储数值 (Key: 完整点位名, Value: 数值)
    # 例如: {"TI1352A_DACA_PV": 123.45, "TIC1201B_PIDA_PV": 88.0}
    values: Dict[str, Any] = Field(default_factory=dict)

    # 存储每个 Tag 的具体质量 (Key: 完整Tag名, Value: Good/Bad)
    qualities: Dict[str, str] = Field(default_factory=dict)

    # 时间字段
    time: datetime = Field(default_factory=now_jst)



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
def parse_opc_data_to_data_view(opc_raw_data: Union[List[tuple], Dict], data_type_tag: str = "采样数据") -> DataView:
    """
    将 OPC 原始数据转换为 DataView 实例 (适配动态字典结构)。

    支持输入格式：
    List: [('Tag.Name', Val, Qual, Time), ...]
    """
    logger.info("解析 OPC 原始数据到 DataView...")
    logger.debug(f"原始数据样本: {str(opc_raw_data)[:500]}")  # 仅打印前500字符以防日志过长
    # 临时存储解析后的数据
    parsed_values: Dict[str, Any] = {}
    parsed_qualities: Dict[str, str] = {}
    first_timestamp = None

    # --- 1. 统一输入格式为列表 ---
    items_to_process = []

    if isinstance(opc_raw_data, list):
        items_to_process = opc_raw_data


    # --- 2. 遍历处理数据 ---
    for item in items_to_process:
        # 确保数据元组至少有前4项 (Tag, Value, Quality, Time)
        if len(item) < 4:
            continue

        tag_name, raw_val, raw_qual, ts_str = item[:4]

        # 确保 tag_name 是字符串 (视情况，你可以在这里做 .replace('_', '.') 的标准化处理)
        tag_key = str(tag_name)
        # tag_key = str(tag_name).replace('_', '.')  # 强制将分隔符转为 .

        # A. 解析时间 (只取第一个非空的有效时间作为该批次时间)
        if ts_str and not first_timestamp:
            try:
                # 清理时间字符串逻辑 (保持你原有的逻辑)
                clean_ts_str = str(ts_str) if ts_str is not None else ""

                # 确保是字符串类型后再进行 in 操作
                if not isinstance(clean_ts_str, str):
                    clean_ts_str = str(clean_ts_str)

                # 安全检查：只有在确认是字符串后才使用 in 操作
                try:
                    if '+' in clean_ts_str:
                        clean_ts_str = clean_ts_str.split('+')[0]
                    elif clean_ts_str.count('-') > 2:
                        last_dash = clean_ts_str.rfind('-')
                        if last_dash > 10:
                            clean_ts_str = clean_ts_str[:last_dash]
                except (TypeError, AttributeError) as check_err:
                    logger.debug(f"时间字符串检查失败: {clean_ts_str}, 错误: {check_err}")

                # 注意：这里假设 timestamp 格式固定
                dt_naive = datetime.strptime(clean_ts_str.strip(), "%Y-%m-%d %H:%M:%S.%f")
                # 假设 LOCAL_TZ 全局变量存在
                first_timestamp = LOCAL_TZ.localize(dt_naive)
            except (ValueError, TypeError) as e:
                logger.debug(f"时间解析失败: {ts_str}, 错误: {e}")
                pass

        # B. 处理质量 (统一转为 'Good' / 'Bad')
        # 很多 OPC Server 返回的 Good 可能是字符串 "Good" 也可能是布尔值 True 或数字 192/1
        is_good = str(raw_qual).upper() in ['GOOD', 'TRUE', '1', '192']
        parsed_qualities[tag_key] = 'Good' if is_good else 'Bad'

        # C. 处理数值 (直接存入 values 字典，不再查表映射)
        # 调用你之前定义的 clean_opc_value 函数
        parsed_values[tag_key] = clean_opc_value(raw_val)

    # --- 3. 组装最终对象 ---

    # 确定最终时间
    final_time = first_timestamp if first_timestamp else now_jst()

    return DataView(
        dataType=data_type_tag,
        values=parsed_values,  # 动态数值字典
        qualities=parsed_qualities,  # 动态质量字典
        time=final_time
    )