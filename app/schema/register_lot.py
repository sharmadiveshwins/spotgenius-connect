from pydantic import BaseModel
from typing import List


class RegisterLotSchema(BaseModel):
    providerKey: str
    parkingLotId: int
    displayName: str
    address: str
    city: str
    state: str
    zip: str
    ianaTimezone: str
    latitude: float
    longitude: float
    signImageUrls: List[str]


class RegisterLotResponseSchema(BaseModel):

    sgParkingLotId: int
    providerParkingLotId: str
