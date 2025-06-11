import uuid
from sqlalchemy import (Column,
                        String, Integer, Boolean
                        )
from app.models.base import Base
from sqlalchemy.orm import Session, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.utils import enum


class ProviderTypes(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)
    text_key = Column(String, nullable=True)
    name = Column(String, nullable=False)
    is_visible = Column(Boolean, nullable=False, default=True)

    providers = relationship("Provider", back_populates="provider_type")

    @classmethod
    def get_by_id(cls, db: Session, provider_id: int):
        return db.query(cls).get(provider_id)

    @classmethod
    def get_by_text_key(cls, db: Session, text_key: str):
        provider_type = db.query(ProviderTypes).filter(ProviderTypes.text_key == text_key).one()
        return provider_type

    @classmethod
    def get_all_provider_types(cls, db: Session):
        # items = db.query(Item).filter(Item.id != 4).offset(skip).limit(limit).all()

        provider_types = (db.query(ProviderTypes)
                          .filter(cls.is_visible != False)
                          .all())
        return provider_types
