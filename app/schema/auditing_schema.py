from pydantic import BaseModel, Json
from datetime import datetime
from typing import List, Optional, Union, Any


class Events(BaseModel):
    type: str
    description: str
    provider: str = None
    timestamp: datetime
    amount: Optional[float] = None


class SchemaForNUllProviderINSessionLog(BaseModel):
    type: str
    description: str
    timestamp: datetime


class SessionLogWithoutAmountSchema(BaseModel):
    type: str
    description: str
    provider: str = None
    timestamp: datetime


class Session(BaseModel):
    sessionStart: datetime
    session_id: Optional[int] = None
    record_id: Optional[int] = None
    spot_id: Optional[int] = None
    parking_spot_name: Optional[str] = None
    title: str
    isWaitingForPayment: Union[bool, Any] = False
    isWaitingForReservation: Optional[bool] = False
    text_to_show: Optional[str] = None
    total_paid_price: Union[str, Any] = None
    events: List[Union[Events, SchemaForNUllProviderINSessionLog, SessionLogWithoutAmountSchema]]


class Stats(BaseModel):
    total_sessions: int
    active_sessions: int
    in_grace_period: int
    violations: int
    # compliant: int


class Metadata(BaseModel):
    total_records: int
    total_pages: int
    current_page: int
    page_size: int


class AuditingSchema(BaseModel):
    stats: Stats
    providers: Optional[Json] = None
    sessions: List[Session]


class AuditingSchemaV2(BaseModel):
    metadata: Optional[Metadata] = None
    stats: Stats
    group_by_date: bool
    providers: Optional[Json] = None
    sessions: List[List[Session]]


class AuditReqRespCreateSchema(BaseModel):
    api_request: str
    api_response: Optional[str] = None
    api_response_code: Optional[str] = None
    description: Optional[str] = None
    provider_connect_id: int
    task_id: int
    violation_id: Optional[int] = None
