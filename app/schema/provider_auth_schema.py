from typing import List

from pydantic import BaseModel
from datetime import datetime


class PaymentProviderAuth(BaseModel):

    class ParkMobileSchema(BaseModel):
        client_id: str
        client_secret: str

    class ObbeoSchema(BaseModel):
        pass


class ReservationProvider(BaseModel):
    pass


class EnforcementProvider(BaseModel):

    class RegisterLotWithProvider(BaseModel):
        code: str
        displayName: str
        address: str
        city: str
        state: str
        zip: str
        ianaTimezone: str
        latitude: float
        longitude: float
        signImageUrls: List[str]

    class ConnectWithProviderSchema(BaseModel):
        connect_id: int
        provider_id: int
        facility_id: str
        feature_event_type_ids: int



