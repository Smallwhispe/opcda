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


class PredictResult(BaseModel):
    id: Optional[int] = None
    pressure: Optional[str] = None
    c5: Optional[str] = None
    bing_xi: Optional[str] = None
    gan_dian: Optional[str] = None
    # 确保 time 字段存储的是带时区的 datetime 对象
    time: datetime = Field(default_factory=now_jst)

    def __repr__(self):
        return (f"PredictResult(id='{self.id}', "
                f"pressure='{self.pressure}', "
                f"c5='{self.c5}', "
                f"bing_xi='{self.bing_xi}', "
                f"gan_dian={self.gan_dian}, "
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
            'pressure': self.pressure,
            'c5': self.c5,
            'bing_xi': self.bing_xi,
            'gan_dian': self.gan_dian,
            'time': time_str_final  # 使用本地时区格式化的字符串
        }