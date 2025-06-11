import logging

import requests
from fastapi import HTTPException
from requests.auth import HTTPBasicAuth
from sqlalchemy.orm import Session
from app import schema
from app.config import settings
from fastapi.encoders import jsonable_encoder
from typing import List
from app.utils.schema_mapping import SchemaMapping
from app.models import base

logger = logging.getLogger(__name__)


def lot_register_service(register_schema: List[schema.RegisterLotSchema],
                         db: Session) -> schema.RegisterLotResponseSchema:
    for obj in register_schema:
        lot_id = base.ConnectParkinglot.get_connect_parking_lot_id(db, obj.parkingLotId)
        provider_obj = base.Provider.get_provider_by_text_key(db, obj.providerKey)
        if lot_id:
            create = base.AuditRequestResponse.create_audit_req_resp(db, jsonable_encoder(register_schema))
            park_pliant_schema = [SchemaMapping.map_values_to_park_pliant_schema(item) for item in register_schema]
            auth = HTTPBasicAuth(settings.PARK_PLAINT_AUTH_USER, settings.PARK_PLAINT_AUTH_PASSWORD)
            encoder_json = jsonable_encoder(park_pliant_schema, by_alias=True)
            try:
                request_park_pliant = requests.post(
                    settings.PARK_PLAINT_BASE_URL + "/lots",
                    auth=auth,
                    json=encoder_json
                )
                request_park_pliant.raise_for_status()
                # TODO
                base.AuditRequestResponse.update(db, create.id, request_park_pliant.json())
                get_parking_provider_id = request_park_pliant.json().get("id")
                provider_connect_schema = schema.EnforcementProvider.ConnectWithProviderSchema(
                    connect_id=lot_id.id,
                    provider_id=provider_obj.id,
                    facility_id=get_parking_provider_id,
                    feature_event_type_ids=2)
                base.ProviderConnect.create(db, provider_connect_schema)
                response_schema = schema.RegisterLotResponseSchema(sgParkingLotId=lot_id.id,
                                                                   providerParkingLotId=get_parking_provider_id)
                return response_schema
            except Exception as e:
                logger.critical(f"Exception: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error sending request to Park Plaint API: {str(e)}")
        raise HTTPException(status_code=500, detail=f"parking lot is not exist with id {obj.parkingLotId}")
