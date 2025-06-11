from pydantic import BaseModel
from typing import Optional, List
from sqlite3 import Timestamp


class TaskCreateSchema(BaseModel):
    status: Optional[str] = None
    event_type: str
    parking_lot_id: int
    session_id: Optional[int] = None
    parking_spot_id: Optional[int] = None
    parking_spot_name: Optional[str] = None
    next_at: Optional[Timestamp] = None
    plate_number: Optional[str] = None
    state: Optional[str] = None
    feature_text_key: str
    sgadmin_alerts_ids: Optional[List[int]] = None
    sg_event_response: Optional[dict] = None
    provider_type: int


class TaskUpdateSchema(BaseModel):
    status: Optional[str] = None
    event_type: Optional[str] = None
    parking_lot_id: Optional[str] = None
    parking_spot_id: Optional[int] = None
    parking_spot_name: Optional[str] = None
    next_at: Optional[Timestamp] = None
    plate_number: Optional[str] = None
    state: Optional[str] = None
    feature_text_key: Optional[str] = None
    sgadmin_alerts_ids: Optional[List[int]] = None
    sg_event_response: Optional[dict] = None
    provider_type: Optional[int] = None
