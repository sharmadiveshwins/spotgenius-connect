import secrets
import hashlib
from fastapi import HTTPException, Depends

from app.dependencies.deps import get_db
from app.models.base import Base
from sqlalchemy import (Column, Integer, String)
from typing import Optional
from sqlalchemy.orm import Session
from app import schema
from app.utils.security import get_hashed_oauth_client_secret


class User(Base):

    id = Column(Integer, primary_key=True)
    user_name = Column(String, nullable=False)
    password = Column(String, nullable=False)
    client_id = Column(String, nullable=False)
    client_secret = Column(String, nullable=False)
    token = Column(String, nullable=True)

    @classmethod
    def generate_new(cls,
                     db: Session,
                     client_name: str
                     ):
        client_secret = secrets.token_urlsafe(32)
        client = User(user_name=client_name,
                      password=get_hashed_oauth_client_secret(client_secret),
                      client_id=secrets.token_urlsafe(32),
                      client_secret=get_hashed_oauth_client_secret(client_secret),
                      )
        db.add(client)
        db.commit()
        db.refresh(client)

        return client

    @classmethod
    def verify_password(cls, plain_password, hashed_password):
        return hashlib.sha256(plain_password.encode("utf-8")).hexdigest() == hashed_password

    @classmethod
    def authenticate_user(cls, client_id: str, client_secret: str, db: Session = Depends(get_db)):

        client = db.query(cls).filter(
            cls.client_id == client_id,
            cls.client_secret == client_secret,
        )
        return client.first()

    @classmethod
    def get_by_client_id(cls, db, client_id: str):
        return db.query(cls).filter(cls.client_id == client_id).first()
    
    @classmethod
    def get_by_user_name(cls, db, user_name: str):
        return db.query(cls).filter(cls.user_name == user_name).first()

