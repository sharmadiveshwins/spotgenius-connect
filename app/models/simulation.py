from sqlalchemy import (Column, ForeignKey, Integer, JSON, Enum)
from app.models.base import Base
from sqlalchemy import func, cast, TIMESTAMP
from sqlalchemy.orm import Session

class Simulation(Base):
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    provider_id = Column(Integer, ForeignKey("provider.id"), name="fk_provider_id", nullable=False)
    input_data = Column(JSON, nullable=False)
    api_type = Column(
        Enum('reservation', 'monthly_pass', 'guest_info', name='api_type'),
        nullable=False
    )

    @classmethod
    def filterTibaRecords(cls, db: Session, ValidFromKey, ValidToKey, ValidFrom, ValidTo, provider_id, api_type):
        items = db.query(cls).filter(
            func.to_timestamp(func.json_extract_path_text(cls.input_data, ValidToKey), 'DD-MM-YYYY"T"HH24:MI:SS') >= ValidFrom,
            func.to_timestamp(func.json_extract_path_text(cls.input_data, ValidFromKey), 'DD-MM-YYYY"T"HH24:MI:SS') <= ValidTo
        ).filter(
            cls.provider_id == provider_id,
            cls.api_type == api_type
        ).all()
        
        return [item.input_data for item in items]