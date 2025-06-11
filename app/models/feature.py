import uuid
from sqlalchemy import (Column,
                        String,
                        Integer, asc, Enum, Boolean, and_
                        )
from app.models.base import Base
from sqlalchemy.orm import Session, aliased

from app.utils.enum import FeatureType
from app.models import base


class Feature(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    text_key = Column(String, nullable=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    feature_type = Column(Enum(FeatureType, create_type=True), nullable=False, default=FeatureType.UNDEFINED)
    is_enabled = Column(Boolean, nullable=False, default=True)

    @classmethod
    def get(cls, db: Session, id: int):
        return db.query(cls).get(id)
    
    @classmethod
    def get_by_text_key(cls, db: Session, key: str):
        return db.query(cls).filter(cls.text_key == key).first()

    @classmethod
    def get_all_features(cls, db: Session):
        return db.query(cls).order_by(asc(cls.id)).all()

    @classmethod
    def get_enabled_feature_by_provider_id(cls, db: Session, provider_id: int):
        pf_alias = aliased(base.ProviderFeature)
        query = (
            db.query(base.Feature)
            .join(pf_alias, base.Feature.id == pf_alias.feature_id)
            .filter(
                and_(
                    pf_alias.provider_id == provider_id,
                    base.Feature.is_enabled == True
                )
            )
        )
        results = query.all()
        return results
    
    @classmethod
    def get_all_by_text_key(cls, db: Session, keys: tuple):
        return db.query(cls).filter(cls.text_key.in_(keys)).all()
