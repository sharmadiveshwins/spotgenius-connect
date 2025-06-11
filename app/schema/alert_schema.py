from typing import Optional, List, Literal
from pydantic import BaseModel


class AlertCreateSchema(BaseModel):
    title: str
    severity: Optional[Literal['high', 'medium', 'low']] = None
    category: Literal['infrastructure', 'violation', 'system_error', 'informational_events', 'admin_generated']
    subcategory: Optional[str] = None
    alert_type: Optional[Literal['info', 'error']] = None
    alert_type_id: Optional[int] = None
    parking_lot_id: Optional[int] = None
    parking_spot_id: Optional[str] = None
    special_area_id: Optional[int] = None
    camera_id: Optional[int] = None
    image_base64s: Optional[List[str]] = None
    details: Optional[str] = None
    license_plate_number: Optional[str] = None
    alert_state: Literal['open', 'closed']
    alert_trigger_state: Optional[Literal['active', 'inactive', 'unsure']] = None
    duration_minutes: Optional[int] = None


class AlertUpdateSchema(BaseModel):
    id: int
    alert_state: Literal['open', 'closed']
    alert_trigger_state: Literal['active', 'inactive', 'unsure']
    inactive_reason: str
