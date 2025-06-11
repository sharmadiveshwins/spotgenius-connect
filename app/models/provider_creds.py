from sqlalchemy import (Column,
                        String,
                        Integer,
                        JSON,
                        TIMESTAMP, ForeignKey, DateTime
                        )
from app.models.base_class import Base
from sqlalchemy.orm import Session
from app import schema
import datetime



class ProviderCreds(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    text_key = Column(String, nullable=False)
    client_id = Column(String, nullable=False)
    client_secret = Column(String, nullable=False)
    api_key = Column(String, nullable=True)
    access_token = Column(String, nullable=True)
    expire_time = Column(TIMESTAMP, nullable=True)
    meta_data = Column(JSON, nullable=True)
    provider_id = Column(Integer, ForeignKey("provider.id"), name="fk_provider_id", nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    def provider_cred_to_dict(self):
        return {
            "provider_cred_id": self.id,
            "text_key": self.text_key,
            "provider_id": self.provider_id
        }

    @classmethod
    def create(cls, db: Session, create_provider_creds_schema: schema.CreateProviderCredsSchema):
        provider_creds = cls(**create_provider_creds_schema.model_dump())
        db.add(provider_creds)
        db.flush()
        # db.commit()
        # db.refresh(provider_creds)
        return provider_creds

    @classmethod
    def get_by_provider(cls, db: Session, provider_id: int):
        provider_creds = db.query(cls).filter(cls.provider_id == provider_id).all()
        return provider_creds

    @classmethod
    def get_by_id(cls, db: Session, cls_id: int):
        get_by_id = db.query(cls).get(cls_id)
        if get_by_id:
            return get_by_id

    @classmethod
    def get_provider_creds(cls, db, provider_creds_id: int):
        provider_creds = db.query(cls).filter(cls.id == provider_creds_id).first()
        return provider_creds

    @classmethod
    def update(cls, db: Session,
               provider_id: int,
               update_token: schema.SaveToken
               ):

        provider_creds = cls.get_provider_creds(db, provider_id)
        if provider_creds:
            provider_creds.access_token = update_token.access_token
            provider_creds.expire_time = update_token.expire_time
            db.add(provider_creds)
            db.commit()
            db.refresh(provider_creds)
        return provider_creds

    @classmethod
    def update_by_id(cls,
                     db: Session,
                     cred_id: int,
                     data_to_update: schema.UpdateCred):

        provider_creds = db.query(cls).get(cred_id)
        if provider_creds:
            for key, value in data_to_update.model_dump().items():
                setattr(provider_creds, key, value)
            db.commit()
            return provider_creds
        else:
            return None

    @classmethod
    def update_token(cls, db: Session,
                     cred_id: int,
                     token: str
                     ):

        provider_creds = db.query(cls).get(cred_id)
        if provider_creds:
            provider_creds.access_token = token
            db.add(provider_creds)
            db.commit()
            db.refresh(provider_creds)
        return provider_creds


    @classmethod
    def soft_delete_provider_cred(cls, db: Session, cred_id: int):
        provider_cred = db.query(ProviderCreds).filter(ProviderCreds.id == cred_id).first()
        if provider_cred:
            provider_cred.deleted_at = datetime.datetime.utcnow()  # Mark as deleted
            db.commit()
            db.refresh(provider_cred)
        return provider_cred