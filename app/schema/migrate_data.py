from datetime import datetime
from typing import Any

from pydantic import BaseModel


class TaskData(BaseModel):
    id: int
    event_type: str
    plate_number: str
    parking_lot_id: int
    created_at: datetime
    sgadmin_alerts_ids: Any
