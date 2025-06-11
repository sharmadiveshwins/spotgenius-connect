from typing import Union, Optional, Any
from sqlite3 import Timestamp
from pydantic import BaseModel


class Violation(BaseModel):
    name: str
    status: str
    session: str
    description: str
    task_id: Optional[int] = None
    amount_due: Optional[Union[float, int]] = None
    plate_number: Union[str, None]
    parking_spot_id: Optional[Union[int, None]]
    parking_lot_id: Optional[Union[int, None]]
    violation_type: str
    session_id: Union[int, None]
    meta_data: Any
    violation_event: Optional[Any] = None
    timestamp: Optional[Timestamp] = None
