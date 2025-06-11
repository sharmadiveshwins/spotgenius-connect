from pydantic import BaseModel
from typing import Optional, List, Dict, Union
from sqlite3 import Timestamp


class SgSessionAudit(BaseModel):
    entry_event: Optional[Dict] = None
    exit_event: Optional[Dict] = None
    parking_lot_id: int
    lpr_number: Optional[str] = None
    parking_spot_name: Optional[str] = None
    spot_id: Optional[int] = None
    session_start_time: Timestamp = None
    lpr_record_id: int = None
    has_nph_task: bool = False
    is_active: Optional[bool] = True
    is_waiting_for_payment: Optional[bool] = None


class SgSessionLog(BaseModel):

    session_id: int
    action_type: str
    description: Optional[str] = None
    meta_info: Optional[Dict] = None
    provider: Optional[Union[int, None]] = None
    event_at: Optional[Timestamp] = None

