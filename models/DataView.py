from pydantic import BaseModel
from sqlalchemy import String, VARCHAR

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from dataclasses import dataclass

db = SQLAlchemy()

@dataclass
class DataView(db.Model):
    __tablename__ = 'data_view'
    id = db.Column(VARCHAR(45),primary_key=True)
    temperature = db.Column(VARCHAR(45))
    liquid = db.Column(VARCHAR(45))
    pressure = db.Column(VARCHAR(45))
    time = db.Column(MEDIUMTEXT)

    def __repr__(self):
        return (f"DataView(id='{self.id}', "
                f"temperature='{self.temperature}', "
                f"liquid='{self.liquid}', "
                f"pressure={self.pressure}, "
                f"time={self.time}, )")
    def to_dict(self):
        return {
            'id': self.id,
            'temperature': self.temperature,
            'liquid': self.liquid,
            'pressure': self.pressure,
            'time': self.time
        }