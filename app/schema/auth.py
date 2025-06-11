from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Auth(BaseModel):
    username: str
    password: str


# class OauthSchema(BaseModel):
#     text_key: str
#     id: int = None


class SaveToken(BaseModel):
    access_token: str
    expire_time: Optional[datetime] = None
