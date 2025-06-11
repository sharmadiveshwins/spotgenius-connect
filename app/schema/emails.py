from pydantic import BaseModel
from typing import List


class EmailSchema(BaseModel):
    to_emails: List[str]
    subject: str
    body: str
