from typing import Optional, List
from pydantic import BaseModel


class CreateAlert(BaseModel):
    title: str
    category: str
    alert_action: str = None
    alert_state: str
    alert_trigger_state: str = None
    severity: Optional[str]
    alert_type: Optional[str]
    alert_type_id: Optional[int] = None
    organization_id: Optional[int] = None
    parking_lot_id: Optional[int]
    parking_spot_id: Optional[int] = None
    special_area_id: Optional[int] = None
    camera_id: Optional[int] = None
    image_path: Optional[str] = None
    image_paths: Optional[list[str]] = None
    details: Optional[str] = None
    license_plate_number: Optional[str] = None
    state_updated_at: Optional[str] = None
    state_updated_by_org_user_id: Optional[int] = None
    duration_minutes: Optional[int] = None
    image_base64s: Optional[List]


class UpdateAlert(BaseModel):
    id: int
    alert_state: str
    alert_trigger_state: str
