import requests
import logging
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder

from app.config import settings
from requests.auth import HTTPBasicAuth
from fastapi.responses import JSONResponse
from app.models import base
from app.utils.schema_mapping import SchemaMapping
from app import schema
from app.utils import enum


logger = logging.getLogger(__name__)


class ParkPliantService:

    @staticmethod
    def register_lot(db, register_schema):
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

    @staticmethod
    def register_callbacks_service(db, callback_schema):
        provider = base.Provider.get_by_name(db, enum.Provider.PROVIDER_PARK_PLIANT.value)
        auth = HTTPBasicAuth(provider.client_id, provider.client_secret)
        response = requests.post(provider.api_endpoint + "/callbacks",
                                 auth=auth,
                                 json={
                                     "authorization": "Basic" + settings.CALLBACKS_AUTHORIZATION_TOKEN,
                                     "correctionUrl": callback_schema.correctionUrl,
                                     "paymentUrl": callback_schema.paymentUrl,
                                     "noticeUrl": callback_schema.noticeUrl,
                                     "disputeUrl": callback_schema.disputeUrl
                                 })
        payload = response.json()
        if response.status_code == 200:
            return JSONResponse(content={"message": "Callbacks are registered successfully.", "payload": payload},
                                status_code=200)
        else:
            return JSONResponse(content={"message": "Error", "payload": payload}, status_code=400)

    @staticmethod
    def correction(db, correction_schema):
        return base.ParkPliantCallback.insert_callbacks(db, correction_schema, "correction")

    @staticmethod
    def payment(db, payment_schema):
        return base.ParkPliantCallback.insert_callbacks(db, payment_schema, "payment")

    @staticmethod
    def notice(db, notice_schema):
        return base.ParkPliantCallback.insert_callbacks(db, notice_schema, "notice")
