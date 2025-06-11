from sqlite3 import Timestamp
from typing import Optional, List, Union
from pydantic import BaseModel


class Event(BaseModel):
    timestamp: str
    event_type: str


class Price(BaseModel):
    usd: str


class Resource(BaseModel):
    resource_type: str
    created_at: Timestamp
    updated_at: Timestamp
    cancelled_at: Optional[Timestamp]
    start_date_time: Timestamp
    end_date_time: Timestamp
    resource_id: str
    type: str
    license_plate: str
    first_name: str
    last_name: str
    user_id: int
    full_price: Price
    price_paid: Price
    seller_gross_price: Price
    location_name: str
    location_id: int


class RequestData(BaseModel):
    event: Event
    resource: Resource


class PushPaymentSchema(BaseModel):
    start_date_time: Timestamp
    end_date_time: Timestamp
    price_paid: str
    plate_number: Optional[str] = None
    spot_id: Optional[str] = None
    original_response: str
    external_reference_id: Optional[int] = None
    provider_id: int
    location_id: Optional[int] = None


class PullPaymentSchema(BaseModel):
    location_id: Optional[int] = None


class PullPaymentSchemaBySpot(BaseModel):
    provider_id: int
    spot_id: str
    location_id: Optional[Union[int, str]]
    parking_lot_id: Optional[int] = None


class SgAdminRequestData(BaseModel):
    challenge_key: str


class ArrivePushPriceSchema(BaseModel):
    USD: str


class ArrivePushEventSchema(BaseModel):
    type: str


class ArrivePushResourceSchema(BaseModel):
    resource_type: str
    location_id: int
    location_name: str
    license_plate: str
    start_date_time: Timestamp
    end_date_time: Timestamp
    price_paid: ArrivePushPriceSchema
    full_price: ArrivePushPriceSchema
    seller_gross_price: ArrivePushPriceSchema
    venue_id: Optional[int]
    amenities: Optional[List]


class ArrivePushSchema(BaseModel):
    event: ArrivePushEventSchema
    resource: ArrivePushResourceSchema

