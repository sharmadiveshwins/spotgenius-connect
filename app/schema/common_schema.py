from pydantic import BaseModel, field_validator, validator
from typing import Optional, List, Any, Union
from datetime import datetime


class CommonSchema(BaseModel):
    plateNumber: Optional[str] = None
    parking_spot_id: Optional[int] = None
    parking_lot_id: int
    facility_id: Optional[str] = None


class CreateProviderConnectSchema(BaseModel):
    facility_id: str
    connect_id: int
    provider_creds_id: int


class ProviderFeatureSchema(BaseModel):
    parking_lot_id: int
    provider_id: int
    feature_id: int


class ApiResponseSchema(BaseModel):
    message: str
    status: str
    data: List[Any]


class ProviderTypeSchema(BaseModel):
    id: int
    text_key: str
    name: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class FeatureSchema(BaseModel):
    id: int
    text_key: str
    name: str
    description: str
    feature_type: str
    is_enabled: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class EventTypesSchema(BaseModel):
    id: int
    text_key: str
    name: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class ProviderCredsSchema(BaseModel):
    id: int
    text_key: Optional[str] = None
    client_id: Optional[str] = None
    access_token: Optional[str] = None
    expire_time: Optional[datetime] = None
    provider_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProviderCredsResponseSchema(BaseModel):
    id: int
    text_key: Optional[str] = None
    client_id: Optional[str] = None
    expire_time: Optional[datetime] = None
    provider_id: Optional[int] = None
    meta_data: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# TODO need to implement these
class ParkinglotProviderFeatureCreateSchema(BaseModel):
    # provider_connect_id: int
    provider_connect_id: int
    feature_id: Union[str, int]


class AttachFeatureSchema(BaseModel):
    parking_lot_provider_features: List[ParkinglotProviderFeatureCreateSchema]


class ProviderConnectSchema(BaseModel):
    facility_id: Optional[int] = None
    connect_id: Optional[int] = None
    provider_creds_id: Optional[int] = None


class Credentials(BaseModel):
    key: str = None
    label: str = None
    value: Optional[Union[str, int]] = None
    type: Optional[Any] = None


class ConfigSettingsGlobal(BaseModel):
    parking_lot: List[int]
    credentials: List[Credentials]
    meta_data: dict
    cred_id: Optional[int] = None


class ConfigSettingsNonGlobal(BaseModel):
    parking_lot: int
    credentials: List[Credentials]
    meta_data: dict
    cred_id: Optional[int] = None


class GetProviderCredsSchema(BaseModel):
    config_settings: Union[List[ConfigSettingsGlobal], List[ConfigSettingsNonGlobal]]
    meta_data: dict = None
    meta_data_list: List[dict] = None

    @field_validator('config_settings')
    def config_settings_not_empty(cls, v):
        if not v:
            raise ValueError('Provider credentials must be provided')
        return v


class ConfigSettings(BaseModel):
    cred_id: Optional[int] = None
    parking_lot: Union[int, List] = None
    credentials: List[Credentials]
    meta_data: dict = None


class NewConfigSettings(BaseModel):
    feature_id: int = 0
    provider_id: int
    auth_level: str
    config_settings: List[ConfigSettings]
    features: List[int] = None
    detach_parking_lots: List[Any] = None


class CreateProviderCredsSchema(BaseModel):
    provider_id: int
    text_key: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    meta_data: Optional[dict] = None
    api_key: Optional[str] = None
    access_token: Optional[str] = None


class UpdateCred(BaseModel):
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    meta_data: Optional[dict] = None
    api_key: Optional[str] = None
    access_token: Optional[str] = None


class FeatureEventType(BaseModel):
    event_type_id: Optional[int] = None
    feature_url_path_id: Optional[int] = None
    parkinglot_provider_feature_id: int
    provider_id: Optional[int] = None

    def exclude_key(self, exclude_keys: Optional[List[str]] = None):
        exclude = set(exclude_keys) if exclude_keys else set()
        return self.dict(exclude=exclude)


class CreateFeatureEventType(BaseModel):
    event_type_id: Optional[int] = None
    feature_url_path_id: Optional[int] = None
    parkinglot_provider_feature_id: int


class AttachEventParkingFeature(BaseModel):
    feature_event_types: List[FeatureEventType]


class ContactDetails(BaseModel):
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    grace_period: Optional[int] = None
    retry_number: Optional[int] = None
    is_in_out_policy: Optional[bool] = True
    pricing_type: Optional[str] = "Fixed"

    def contact_details_to_dict(self):
        return {
            "contact_name": self.contact_name,
            "contact_email": self.contact_email,
            "grace_period": self.grace_period,
            "retry_number": self.retry_number,
            "is_in_out_policy": self.is_in_out_policy,
            "pricing_type": self.pricing_type
        }


class ConnectedProvider(BaseModel):
    id: int
    name: str
    text_key: str
    logo_url: str = None
    auth_type: str
    feature_id: Union[int, List]
    service_type: str
    count_parking_lots: int

    def connected_provider_to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "auth_type": self.auth_type,
            "feature_id": self.feature_id,
            "service_type": self.service_type,
            "count_parking_lots": self.count_parking_lots,
        }


class ProviderDetails(BaseModel):
    contact_details: Optional[ContactDetails] = None
    connected_provider: List[ConnectedProvider]

    def provider_details_to_dict(self):
        return {
            "contact_details": self.contact_details.dict() if self.contact_details else None,
            "connected_provider": [cp.connected_provider_to_dict() for cp in self.connected_provider]
        }


class ConnectFeatureProviderCred(BaseModel):
    auth_level: str
    provider_id: int
    feature_id: int
    config_settings: Union[List[ConfigSettingsGlobal], List[ConfigSettingsNonGlobal]]
    features: List[int] = None


class DeleteRequest(BaseModel):
    provider_cred_id: int
    parking_lot_id: int


class DeleteConnection(BaseModel):
    deletions: List[DeleteRequest]


class NotPaidParkingTiming(BaseModel):
    start_from: Optional[str] = None
    to: Optional[str] = None
    overstay_limit: Optional[int] = 0
    timezone: Optional[str] = None


class MaximumParkTime(BaseModel):
    hours: Optional[Union[int, str]] = None
    minutes: Optional[Union[int, str]] = None


class ParkingTimeframes(BaseModel):
    start_time: str
    end_time: str
    id: Optional[Union[int, str]] = None


class ParkingTimingSchema(BaseModel):
    parking_operations: str
    organization_name: Optional[str] = None
    parking_lot_name: Optional[str] = None
    timezone: str
    max_park_time: Optional[MaximumParkTime] = None,
    parking_timeframes: Optional[List[ParkingTimeframes]] = None

    @validator("max_park_time", pre=True, always=True)
    def ensure_none(cls, value):
        # If the value is a tuple like (None,), return None
        if isinstance(value, tuple) and len(value) == 1 and value[0] is None:
            return None
        return value

    @property
    def max_park_time_in_seconds(self):
        if not self.max_park_time:
            return None
        if not self.max_park_time.hours:
            return int(self.max_park_time.minutes) * 60

        return int(self.max_park_time.hours) * 60 * 60 + int(self.max_park_time.minutes) * 60


class ParkingFeeTimeframe(BaseModel):
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class ParkingLotPaymentTimeframe(BaseModel):
    overstay_limit: Optional[int] = 0
    timezone: Optional[str] = None
    parking_fee_timeframes: List[ParkingFeeTimeframe]


class ParkingTimeSchema(BaseModel):
    start_time: str
    end_time: str
    parking_lot_id: int


class ParkingTimeResponseSchema(BaseModel):
    isProviderConnected: bool
    parking_operations: Optional[str]
    max_park_time: Optional[MaximumParkTime] = None,
    parking_timeframes: Optional[List[ParkingTimeframes]] = []


class SessionsDeleteSchema(BaseModel):
    parking_lot_id: int
    delete_from_datetime: Optional[datetime] = None
