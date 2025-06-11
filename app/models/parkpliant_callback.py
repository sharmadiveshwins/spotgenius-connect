import json

from app.models.base import Base
from sqlalchemy import Column, Integer, Text


class ParkPliantCallback(Base):
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    response = Column(Text, nullable=False)
    callback_type = Column(Text, nullable=False)

    @classmethod
    def insert_callbacks(cls, db, response, callback_type):
        response_str = json.dumps([correction.to_json() for correction in response])
        insert_record = ParkPliantCallback(response=response_str,
                                           callback_type=callback_type)
        db.add(insert_record)
        db.commit()
        db.refresh(insert_record)
