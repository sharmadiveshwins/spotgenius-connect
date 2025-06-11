from app import schema
from app.models.base_class import Base
from sqlalchemy import (Integer, Column, JSON, ForeignKey, String, Text)
from sqlalchemy.orm import relationship

from app.schema import Session


class EnforcementResponseStore(Base):

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    response = Column(JSON, nullable=True)


    @classmethod
    def insert_enforcement_response(cls, db: Session, plate_number: str, provider_id: int, response_data: dict,
                                    ticket_number: str = None):
        try:
            new_entry = cls(response=response_data)
            db.add(new_entry)
            db.commit()
            return new_entry
        except Exception as e:
            db.rollback()
            print(f"Error occurred: {e}")
            return None


