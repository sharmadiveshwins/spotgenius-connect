import uuid
from sqlalchemy import (Column,
                        String,
                        ForeignKey, Integer
                        )
from sqlalchemy.orm import Session
from app.models import base
from app.models.base import Base
from sqlalchemy.dialects.postgresql import UUID
from app import schema


class FeatureEventType(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type_id = Column(Integer, ForeignKey("event_types.id"), name="fk_event_types"
                           , nullable=False)
    feature_url_path_id = Column(Integer,
                                 ForeignKey("feature_url_path.id"),
                                 name="fk_url_path_id", nullable=True)
    parkinglot_provider_feature_id = Column(Integer, ForeignKey("parkinglot_provider_feature.id"),
                                            name="fk_parkinglot_provider_feature"
                                            , nullable=True)

    def to_dict(self):
        return {
            'feature_event_type_id': self.id,
            'event_type_id': self.event_type_id,
            'feature_url_path_id': self.feature_url_path_id,
            'parkinglot_provider_feature_id': self.parkinglot_provider_feature_id,
        }

    @classmethod
    def create(cls, db: Session, request: schema.FeatureEventType):
        feature_event = cls(**request)
        db.add(feature_event)
        db.flush()  # Flush the changes to generate the ID without committing
        db.refresh(feature_event)
        return feature_event

    @classmethod
    def create_feature_event_type(cls, db: Session, create_feature_event_type_schema: schema.CreateFeatureEventType):
        feature_event = cls(**create_feature_event_type_schema.model_dump())
        db.add(feature_event)
        db.commit()
        db.refresh(feature_event)
        return feature_event

    @classmethod
    def get_by_id(cls, db: Session, feature_event_id: int):
        return db.query(cls).get(feature_event_id)

    @classmethod
    def get_provider_feature_obj(cls, db: Session, feature_id: int):
        # Getting all objects with the same feature_id
        return db.query(cls).filter(cls.feature_id == feature_id).all()

    @classmethod
    def get_all_feature_by_provider_connect_and_event_type(cls, db: Session,
                                                           provider_connect_id: int,
                                                           event_type: str):
        feature_event_type = db.query(FeatureEventType).join(
            base.EventTypes, FeatureEventType.event_type_id == base.EventTypes.id
        ).filter(
            FeatureEventType.provider_connect_id == provider_connect_id,
            base.EventTypes.text_key == event_type
        ).first()

        return feature_event_type

    @classmethod
    def get_attached_feature_event_type(cls, db: Session,
                                        event_type_id: int, feature_url_path_id: int,
                                        parkinglot_provider_feature_id: int):
        feature_event_type = (db.query(cls).
                              filter(cls.event_type_id == event_type_id,
                                     cls.feature_url_path_id == feature_url_path_id,
                                     cls.parkinglot_provider_feature_id == parkinglot_provider_feature_id).first())
        return feature_event_type

    @classmethod
    def get_by_parkinglot_provider_feature(cls, db: Session, parkinglot_provider_feature_id: int):

        parkinglot_provider_feature_id = db.query(
            cls
        ).filter(
            cls.parkinglot_provider_feature_id == parkinglot_provider_feature_id
        ).first()

        if parkinglot_provider_feature_id:
            return parkinglot_provider_feature_id

    @classmethod
    def get_all_by_provider_connect_and_feature(cls, db: Session, provider_connect_id: int, feature_id: int):
        subquery = db.query(base.ParkinglotProviderFeature.id).filter(
            base.ParkinglotProviderFeature.provider_connect_id == provider_connect_id,
            base.ParkinglotProviderFeature.feature_id == feature_id
        ).subquery()
        query = db.query(FeatureEventType).filter(
            FeatureEventType.parkinglot_provider_feature_id.in_(subquery)
        )
        return query.all()

    @classmethod
    def delete(cls, db: Session, feature_event_type_id: int):
        db.query(cls).filter(cls.id == feature_event_type_id).delete()
        db.commit()

    @classmethod
    def delete_attached_feature_event_type(cls, db: Session,
                                        event_type_id: int, feature_url_path_id: int,
                                        parkinglot_provider_feature_id: int):
        db.query(cls).filter(
            cls.event_type_id == event_type_id,
            cls.feature_url_path_id == feature_url_path_id,
            cls.parkinglot_provider_feature_id == parkinglot_provider_feature_id
        ).delete()
