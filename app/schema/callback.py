from datetime import datetime

from pydantic import BaseModel
from typing import Optional


class Callbacks(BaseModel):
    correctionUrl: str = None
    paymentUrl: str = None
    noticeUrl: str = None
    disputeUrl: str = None


class Correction(BaseModel):
    referenceId: str
    plate: str
    state: str
    make: str
    void: str

    def to_json(self):
        return {
            "referenceId": self.referenceId,
            "plate": self.plate,
            "state": self.state,
            "make": self.make,
            "void": self.void
        }


class Payment(BaseModel):
    referenceId: str
    date: datetime
    amount: float


class Notice(BaseModel):
    referenceId: str
    type: str
    date: datetime
    contentUrl: Optional[str] = None
    deliverTo: Optional[str] = None






