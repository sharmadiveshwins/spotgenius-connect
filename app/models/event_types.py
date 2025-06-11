from sqlalchemy import (Column,
                        String,
                        Integer
                        )
from app.models.base import Base
from sqlalchemy.orm import Session


class EventTypes(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)
    text_key = Column(String, nullable=True)
    name = Column(String, nullable=False)

    @classmethod
    def get_by_id(cls, db: Session, event_id: int):
        event_obj = db.query(cls).get(event_id)
        return event_obj

    @classmethod
    def get_by_text(cls, db: Session, text_key: str):
        events = db.query(cls).filter(cls.text_key == text_key)
        return events

    @classmethod
    def get_all_events(cls, db: Session):
        events__all = db.query(cls).all()
        return events__all

    @classmethod
    def get_events_by_text_key(cls, db: Session, text_key: []):
        events = db.query(cls).filter(cls.text_key.in_(text_key)).all()
        return events
