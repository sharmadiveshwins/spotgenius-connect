from pydantic import BaseModel
from typing import Optional


class SubTaskCreateSchema(BaseModel):
    task_id: int
    status: Optional[str] = None
    provider_creds_id: int
    feature_url_path: int
