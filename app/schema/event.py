from pydantic import BaseModel
from typing import Optional, List, Dict, Union, Any
from datetime import datetime
from sqlite3 import Timestamp


class TaskCreateSchema(BaseModel):
    event_status: str = None
    event_type: str
    parking_lot_id: int
    parking_spot_id: Optional[int] = None
    next_at: Optional[Timestamp] = None
    plate_number: Optional[str] = None
    state: Optional[str] = None
    feature_text_key: str
    sgadmin_alerts_ids: Optional[List[int]] = None
    sg_event_response: Optional[dict] = None
    provider_type: int


class TaskSchema(BaseModel):
    parking_lot_id: int
    event_type: str = None
    next_at: datetime = None
    provider_type: int = None
    feature_text_key: str = None
    plate_number: Optional[str] = None
    parking_spot_id: Optional[str] = None
    parking_spot_name: Optional[str] = None
    state: Optional[str] = None
    providers_connects: Optional[List[dict]] = None
    sgadmin_alerts_ids: Optional[List[int]] = None
    sg_event_response: Optional[dict]
    session_id: Optional[int] = None

    def to_dict(self):
        return {
            "parking_lot_id": self.parking_lot_id,
            # "parking_spot_id": self.parking_spot_id,
            # "event_type": self.event_type,
            "event_key": self.event_key,
            "plate_number": self.plate_number,
            "issued": self.issued,
            "state": self.state,
        }


class UpdateTask(BaseModel):
    parking_lot_id: int = None
    parking_spot_id: int = None
    event_type: str = None
    feature_url_path: int = None
    next_at: datetime = None


class SgAnprEventSchema(BaseModel):

    parking_lot_id: int
    parking_lot_name: Optional[str] = None
    lpr_record_id: Optional[int] = None
    vehicle_record_id: Optional[int] = None # added in 54
    history_id: Optional[int] = None # added in 54
    session_id: Optional[str] = None
    is_simulated: Optional[str] = None
    event_key: str
    entry_time: Optional[Timestamp] = None
    exit_time: Optional[Timestamp] = None
    license_plate: Optional[str] = None
    timestamp: Timestamp = None
    make: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None
    vehicle_orientation: Optional[str] = None
    region: Optional[str] = None
    frame_image_url: Optional[str] = None
    vehicle_crop_image_url: Optional[str] = None
    lpr_crop_image_url: Optional[str] = None
    violation: Optional[str] = None
    sgadmin_alerts_ids: Optional[List[int]] = None
    # BELOW ARE ADDED TO HANDLE PARKING SPOT UPDATES
    parking_spot_id: Optional[int] = None
    parking_spot_name: Optional[str] = None
    spot_status: Optional[str] = None
    details: Optional[str] = None
    is_unknown: Optional[bool] = None
    unknown_reason: Optional[str] = None
    total_available_spots: Optional[int] = None
    total_unavailable_spots: Optional[int] = None
    # Added to handle violation event
    alert_id: Optional[int] = None
    alert_title: Optional[str] = None
    alert_type_id: Optional[int] = None
    anpr_record_id: Optional[int] = None
    max_park_time_seconds: Optional[int] = None
    image_urls:  Optional[List[Union[Any, str]]] = None
    request_flag: Optional[int] = 0
    disable_spot_payment: Optional[bool] = None
    spot_payment_grace_period: Optional[int] = None
    zone_payment_grace_period: Optional[int] = None
    vehicle_metadata: Optional[Union[dict, Any]] = None
    # force exit keys
    manually_triggered: Optional[bool] = False



    def to_dict(self):
        return self.dict()

