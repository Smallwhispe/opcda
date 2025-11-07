from datetime import datetime
from typing import Optional
from uuid import uuid4

import pytz
from pydantic import BaseModel, Field

LOCAL_TZ = pytz.timezone("Asia/Shanghai")

def now_jst() -> datetime:
    # 生成带时区的当前时间（pytz 的推荐写法）
    return LOCAL_TZ.localize(datetime.now())

class DataView(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    dataType:  Optional[str] = None
    temperature: Optional[str] = None
    flow: Optional[str] = None
    pressure: Optional[str] = None
    concentration: Optional[str] = None
    quality: Optional[bool] = False
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
        return {
            'id': self.id,
            'dataType': self.dataType,
            'temperature': self.temperature,
            'flow': self.flow,
            'pressure': self.pressure,
            'concentration': self.concentration,
            'quality': self.quality,
            'time': self.time.strftime("%Y-%m-%d %H:%M:%S")
        }