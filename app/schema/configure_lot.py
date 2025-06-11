from pydantic import BaseModel
from typing import Optional, List, Union, Dict
from datetime import datetime, time


class User(BaseModel):
    user_name: str
    password: str


class ParkingLotSchema(BaseModel):
    parking_lot_id: Optional[int] = None
    contact_email: Optional[str] = None
    contact_name: Optional[str] = None
    parking_lot_name: Optional[str] = None
    grace_period: Optional[int] = 5
    retry_mechanism: Optional[int] = 3
    is_in_out_policy: Optional[bool] = True
    organization_id: Optional[int] = None


    @classmethod
    def model_validate(cls, obj):
        return cls(
            id=obj.id,
            parking_lot_id=obj.parking_lot_id,
            name=obj.name,
            contact_email=obj.contact_email,
            grace_period=obj.grace_period,
            retry_mechanism=obj.retry_mechanism,
            is_in_out_policy=obj.is_in_out_policy
        )

    def parking_lot_schema_to_dict(self):
        return {
            'parking_lot_id': self.parking_lot_id,
            'contact_email': self.contact_email,
            'contact_name': self.contact_name,
            'parking_lot_name': self.parking_lot_name,
            'grace_period': self.grace_period,
            'is_in_out_policy': self.is_in_out_policy,
            'organization_id': self.organization_id,
        }

    class Config:
        orm_mode = True
        model_config = {"from_attributes": True}


class ParkingLotFullSchema(ParkingLotSchema):
    id: int


class UpdateParkingLotSchema(BaseModel):
    parking_lot_id: Optional[int] = None
    contact_email: Optional[str] = ""
    contact_name: Optional[str] = ""
    grace_period: Optional[int] = 5
    retry_mechanism: Optional[int] = 3
    is_in_out_policy: Optional[bool] = True
    organization_id: Optional[int] = None
    pricing_type: Optional[str] = None

    def parking_lot_schema_to_dict(self):
        return {
            'parking_lot_id': self.parking_lot_id,
            'contact_email': self.contact_email,
            'contact_name': self.contact_name,
            'grace_period': self.grace_period,
            'is_in_out_policy': self.is_in_out_policy,
            'organization_id': self.organization_id,
        }

    @property
    def grace_period_in_seconds(self):
        return self.grace_period * 60


class OrgLotSchema(BaseModel):
    org_id: int
    org_name: Optional[str] = None
    parking_lots: List[ParkingLotSchema]


class UpdateLot(BaseModel):
    org_id: int
    parking_lot: List[int]
    updated_properties: UpdateParkingLotSchema


class EventTypes(BaseModel):
    id: int
    text_key: str
    name: str


class CreateProviderSchema(BaseModel):
    name: str
    api_endpoint: str
    oauth_path: Optional[str] = None
    auth_type: str
    provider_type_id: int
    logo: Optional[str] = None
    auth_level: Optional[str] = 'GLOBAL'


class ProviderSchema(BaseModel):
    id: int
    name: str
    text_key: str
    api_endpoint: Optional[str] = None
    auth_type: Optional[str] = None
    provider_type_id: int
    logo: Optional[str] = None
    auth_level: str = None
    credentials: Optional[Union[List, Dict]] = {}
    connected_parking_lots: Optional[List[int]] = None


class ProviderCredSchema(BaseModel):
    id: int


class ProviderFeatureSchema(BaseModel):
    provider: str
    description: str
    feature_type: str
    url_path_id: int


class ProviderResponseSchema(BaseModel):
    id: int
    text_key: str
    name: str
    api_endpoint: str
    oauth_path: Optional[str] = None
    auth_type: str = None
    client_id: str = None
    api_key: str = None
    provider_type_id: int
    access_token: str = None
    expire_time: Optional[datetime] = None
    logo: str = None

    @classmethod
    def model_validate(cls, obj):
        return cls(
            id=obj.id,
            text_key=obj.text_key,
            name=obj.name,
            api_endpoint=obj.api_endpoint,
            oauth_path=obj.oauth_path,
            auth_type=obj.auth_type,
            client_id=obj.client_id,
            api_key=obj.api_key,
            provider_type_id=obj.provider_type_id,
            access_token=obj.access_token,
            expire_time=obj.expire_time,
            # meta_data: json
            logo=obj.logo
        )

    class Config:
        orm_mode = True
        model_config = {"from_attributes": True}


class ProviderConnect(BaseModel):
    # org_id: int
    parking_lot_id: int
    provider_cred: int
    facility_id: int


class ProviderParkinglotSchema(BaseModel):
    # connect_parkinglot_id: int
    # provider_id: int
    # facility_id: int
    feature: str
    provider_connects: List[ProviderConnect]


class ViolationConfigurationSchema(BaseModel):

    duration: Optional[int] = 2
    duration_amount: Optional[int] = 20
    pricing_type: str
    parking_lot_id: int


class ConnectedProvidersSchema(BaseModel):
    id: int
    name: str
