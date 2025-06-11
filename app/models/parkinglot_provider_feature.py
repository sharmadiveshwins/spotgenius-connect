from typing import List

from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import Session, aliased
from app.models.base import Base
from app import schema
from app.models import base


class ParkinglotProviderFeature(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_connect_id = Column(Integer, ForeignKey("provider_connect.id"), name="fk_provider_connect"
                                 , nullable=False)
    feature_id = Column(Integer, ForeignKey("feature.id"), name="fk_feature"
                        , nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'provider_connect_id': self.provider_connect_id,
            'feature_id': self.feature_id,
        }

    @classmethod
    def create(cls, db: Session, schema: schema.ParkinglotProviderFeatureCreateSchema):
        parkinglot_provider_feature = cls(**schema.model_dump())
        db.add(parkinglot_provider_feature)
        db.flush()
        return parkinglot_provider_feature

    @classmethod
    def create_parkinglot_provider_feature(cls, db: Session, schema: schema.ParkinglotProviderFeatureCreateSchema):
        parkinglot_provider_feature = cls(**schema.model_dump())
        db.add(parkinglot_provider_feature)
        db.commit()
        db.refresh(parkinglot_provider_feature)
        return parkinglot_provider_feature

    @classmethod
    def get(cls, db, lot_provider_feature: int):
        get = db.query(cls).get(lot_provider_feature)
        if get:
            return get

    @classmethod
    def get_by_provider_connect(cls, db: Session, provider_connect_id: int):
        parkinglot_provider_feature = db.query(cls).filter(cls.provider_connect_id == provider_connect_id).first()
        if parkinglot_provider_feature:
            return parkinglot_provider_feature

    @classmethod
    def detach_parkinglot_feature(cls, db: Session, feature_id: int, provider_connect_id: int):
        parkinglot_provider_feature = db.query(cls).filter(cls.provider_connect_id == provider_connect_id,
                                                           cls.feature_id == feature_id).first()
        db.delete(parkinglot_provider_feature)
        db.commit()
        return parkinglot_provider_feature

    @classmethod
    def delete(cls, db: Session, parkinglot_provider_feature_id: int):
        db.query(cls).filter(cls.id == parkinglot_provider_feature_id).delete()
        db.commit()

    @classmethod
    def get_by_feature_id(cls, db: Session, feature_id: int):
        return db.query(cls).filter(cls.feature_id == feature_id).all()

    @classmethod
    def get_by_provider_connect_and_feature(cls, db: Session, provider_connect_id: int, feature_id: int):
        parkinglot_provider_feature = db.query(cls).filter(
                cls.provider_connect_id == provider_connect_id,
                cls.feature_id == feature_id
            ).first()
        if parkinglot_provider_feature:
            return parkinglot_provider_feature
