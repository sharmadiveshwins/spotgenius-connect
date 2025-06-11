from sqlalchemy import (Column,
                        String,
                        Integer,
                        JSON,
                        ForeignKey,
                        Enum, or_,
                        Boolean
                        )
from app.models.base_class import Base
from sqlalchemy.orm import Session, relationship
from app import schema
from app.utils.enum import AuthLevel
from app.models.provider_types import ProviderTypes
from app.models.provider_creds import ProviderCreds
from app.models.provider_connect import ProviderConnect


class Provider(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    text_key = Column(String, nullable=True)
    api_endpoint = Column(String, nullable=True)
    oauth_path = Column(String, nullable=True)
    auth_type = Column(String, nullable=False)
    provider_type_id = Column(Integer, ForeignKey("provider_types.id"), name="fk_provider_type_id", nullable=False)
    meta_data = Column(JSON, nullable=True)
    auth_level = Column(Enum(AuthLevel, create_type=True), nullable=False)
    logo = Column(String, nullable=True)
    is_visible = Column(Boolean, nullable=False, default=True)
    provider_api_request_type = Column(String, nullable=False, default="sgconnect")
    api_request_endpoint = Column(String, nullable=True)

    provider_type = relationship("ProviderTypes", back_populates="providers")

    @classmethod
    def get_provider_by_id(cls, db: Session, provider_id: int):
        return db.query(cls).get(provider_id)

    @classmethod
    def get_by_name(cls, db: Session, provider_name: str):
        provider = db.query(cls).filter(cls.name == provider_name).first()
        return provider

    @classmethod
    def get_provider_by_client_id(cls, db: Session, client_id: str):
        return db.query(cls).filter(cls.client_id == client_id).first()

    @classmethod
    def get_provider_by_text_key(cls, db: Session, text_key: str):
        return db.query(cls).filter(cls.text_key == text_key).first()

    @classmethod
    def get_by_id(cls, db: Session, provider_id: int):
        if provider_id is not None:
            provider = db.query(cls).get(provider_id)
            if provider:
                return provider
        return None

    @classmethod
    def get_provider_type(cls, db: Session, provider_id: int) -> int:
        get_provider_type = db.query(Provider).get(provider_id)
        if get_provider_type:
            return get_provider_type.provider_type_id

    @classmethod
    def update(cls, db: Session,
               provider_id: int,
               update_token: schema.SaveToken
               ):

        provider_obj = cls.get_by_id(db, provider_id)
        if provider_obj:
            provider_obj.access_token = update_token.access_token
            provider_obj.expire_time = update_token.expire_time
            db.add(provider_obj)
            db.commit()
            db.refresh(provider_obj)
        return provider_obj

    @classmethod
    def create(cls, db: Session, schema: schema.CreateProviderSchema):
        provider = cls(**schema.model_dump())
        db.add(provider)
        db.commit()
        db.refresh(provider)
        return provider

    @classmethod
    def get_all_providers(cls, db: Session):
        cls__all = db.query(cls).all()
        return cls__all

    @classmethod
    def get_provider_by_provider_type(cls, db: Session, provider_type_text_key:str):
        return db.query(cls).join(
            ProviderTypes, cls.provider_type_id == ProviderTypes.id
        ).filter(
            ProviderTypes.text_key == provider_type_text_key
        ).first()


    @classmethod
    def get_specific_provider(cls, db: Session, provider_type: int,  access_to_view_provider: bool):

        query  = (db.query(cls)
                  .filter(cls.provider_type_id == provider_type)
                  .filter(or_(access_to_view_provider, cls.text_key != "SpotgeniusDemo"))
                  .all()
                  )

        if query:
            return query

    @classmethod
    def get_lot_connected_providers(cls, db: Session, lot_id: int, provider_type: str):
        results = db.query(
                cls.name.label("name"),
                cls.id.label("id"),
                cls.text_key.label("text_key"),
                cls.logo.label("logo")
            ).join(
                ProviderCreds, cls.id == ProviderCreds.provider_id
            ).join(
                ProviderConnect, ProviderConnect.provider_creds_id == ProviderCreds.id
            ).join(
                ProviderTypes, ProviderTypes.id == cls.provider_type_id
            ).filter(
                ProviderConnect.connect_id == lot_id,
                ProviderTypes.text_key == provider_type,
                cls.is_visible == True
            ).all()

        # Convert result to dictionary
        return [{col: getattr(row, col) for col in row._fields} for row in results]
