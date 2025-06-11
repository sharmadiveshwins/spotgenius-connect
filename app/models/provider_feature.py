from sqlalchemy import (Column,
                        Integer,
                        ForeignKey
                        )
from sqlalchemy.orm import Session
from app.models import base
from app import schema
from app.utils import enum


class ProviderFeature(base.Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_id = Column(Integer, ForeignKey("provider.id"), name="fk_provider_id", nullable=False)
    feature_id = Column(Integer, ForeignKey("feature.id"), name="fk_feature", nullable=False)

    @classmethod
    def create(cls, db: Session, provider_feature_create_schema: schema.ProviderFeatureCreateSchema):
        provider_feature = cls(**provider_feature_create_schema.model_dump())
        db.add(provider_feature)
        db.commit()
        db.refresh(provider_feature)
        return provider_feature

    @classmethod
    def get_provider_feature(cls, db: Session, provider_id: int, feature_id: int):
        provider_feature = db.query(cls).filter(cls.provider_id == provider_id, cls.feature_id == feature_id).first()
        if provider_feature:
            return provider_feature

    @classmethod
    def check_enforcement_inactivate_feature(cls, db: Session, provider_id: int):
        feature = base.Feature.get_by_text_key(db, enum.Feature.ENFORCEMENT_NOTIFICATION.value)
        if feature:
            enforcement_inactivate_feature = cls.get_provider_feature(db, provider_id, feature.id)
            if enforcement_inactivate_feature:
                return feature
