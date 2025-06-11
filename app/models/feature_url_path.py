from sqlalchemy import (Column,
                        String,
                        ForeignKey,
                        Integer, Text,
                        Enum, JSON
                        )
from app.models.base import Base
from sqlalchemy.orm import Session
from app.utils.enum import FeatureRequestType


class FeatureUrlPath(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_id = Column(Integer, ForeignKey("provider.id"), name="fk_provider_id", nullable=False)
    provider_feature_id = Column(Integer, ForeignKey("provider_feature.id"), name="fk_provider_feature")
    path = Column(String, nullable=False)
    request_schema = Column(String, nullable=True, default="")
    response_schema = Column(String, nullable=True, default="")
    request_type = Column(Enum(FeatureRequestType, create_type=True), nullable=False)
    request_method = Column(String, nullable=False)
    headers = Column(Text, nullable=True)
    query_params = Column(Text, nullable=True)
    api_type = Column(String, nullable=False)

    @classmethod
    def get_feature_url_path_by_id(cls, db: Session, feature_url_path_id: int):
        return db.query(cls).get(feature_url_path_id)

    @classmethod
    def get_feature_by_provider_id(cls, db: Session, provider_id: int):
        provider_feature = db.query(cls).filter(cls.provider_id == provider_id).all()

        return provider_feature

    @classmethod
    def get_by_provider_feature_id(cls, db, provider_feature_id: int):
        provider_feature = db.query(cls).filter(cls.provider_feature_id == provider_feature_id).first()
        if provider_feature:
            return provider_feature
