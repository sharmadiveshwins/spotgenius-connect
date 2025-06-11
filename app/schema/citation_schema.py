from datetime import datetime
from typing import Union, Optional

from pydantic import BaseModel


class CreateCitationSchema(BaseModel):
    lotCode: str
    issued: str
    plate: str
    state: str
    amountDue: int
    violation: str


class EnforcementServiceSchema(BaseModel):

    lpr: str
    violation_time: datetime
    entry_time: datetime
    amount: Union[int, float, str]
    violation_title: str
    facility_id: str
    feature: str
    provider_key: str
    state: Optional[str] = None
    parking_lot_id: Optional[int] = None
    spot_name: Optional[Union[str, int]] = None
    make: Optional[str] = None
    color: Optional[str] = None
    body: Optional[str] = None
    parking_lot_name: Optional[str] = None
    citation_id: Optional[str] = None
    car_entry_image: Optional[str] = None
    car_plate_image: Optional[str] = None
    violation_image: Optional[str] = None
    provider_api_key: Optional[str] = None
    meta_data: Optional[dict] = {}


