from sqlalchemy import (Column,
                        String,
                        Integer,
                        ForeignKey
                        )
from app.models.base import Base
from sqlalchemy.orm import Session


class EventFeature(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type_id = Column(Integer, ForeignKey("event_types.id"), name="fk_event_types"
                           , nullable=False)
    feature_id = Column(Integer, ForeignKey("feature.id"), name="fk_feature"
                        , nullable=False)

    @classmethod
    def get_feature_event(cls, db: Session, feature_id: int):
        return db.query(cls).filter(cls.feature_id == feature_id).first()

    @classmethod
    def get_feature_events(cls, db: Session, feature_id: int):
        return db.query(cls).filter(cls.feature_id == feature_id).all()
