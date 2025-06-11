from pydantic import BaseModel, validator
from sqlite3 import Timestamp
from typing import Optional, Union, List


class ResponseIntegrationSchema(BaseModel):

    response_id: Optional[List[int]] = None
    price_paid: Optional[Union[str, int, float]] = None
    paid_date: Optional[str] = None
    expiry_date: Optional[str] = None
    provider: Optional[int] = None
    station_price: Optional[str] = None
    station_name: Optional[str] = None
    plate_number: Optional[str] = None
    parking_spot_id: Optional[str] = None
    matched_plate_number: Optional[str] = None
    lpr_match_number: Optional[int] = None
    action_type: Optional[str] = None
    image: Optional[str] = None

