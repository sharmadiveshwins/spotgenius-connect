from typing import Optional
from pydantic import BaseModel


class VerifyPaymentByLprDetail(BaseModel):
    payment_id: Optional[int]
    timestamp: Optional[str]
    status: int = None
