from typing import Optional
from pydantic import BaseModel


class VerifyPayment(BaseModel):
    facility_id: int
    lot_id: int
    spot_id: int
    vehicle_number: str


class VerifyPaymentDetail(BaseModel):
    payment_id: Optional[int]
    timestamp: Optional[str]
    status: int = None
    amount: int = None
