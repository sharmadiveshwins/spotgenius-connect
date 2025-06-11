from pydantic import BaseModel
from typing import Optional


class CreateParkinglotSchema(BaseModel):
    parking_lot_id: int
    organization_id: int
    contact_email: Optional[str] = None
    parking_lot_name: Optional[str] = None
    parking_operations: Optional[str] = None
    maximum_park_time_in_minutes: Optional[int] = None
    grace_period: Optional[int] = 0
    contact_name: Optional[str] = None
    retry_mechanism: Optional[int] = None
    is_in_out_policy: Optional[bool] = None
