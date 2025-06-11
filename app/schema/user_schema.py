from pydantic import BaseModel
from typing import Optional, List
from sqlite3 import Timestamp
from datetime import datetime


class UserSchema(BaseModel):
    id: Optional[int] =  None
    username: Optional[str] = None
    # password: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    # created_at: Optional[Timestamp] = None
    # updated_at: Optional[Timestamp] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # @classmethod
    # def model_validate(cls, obj):
    #     return cls(
    #         id=obj.id,
    #         username=obj.username,
    #         client_id=obj.client_id,
    #         client_secret=obj.client_secret,
    #         created_at=obj.created_at,
    #         updated_at=obj.updated_at,
    #     )
    #
    # class Config:
    #     orm_mode = True
    #     model_config = {"from_attributes": True}

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

