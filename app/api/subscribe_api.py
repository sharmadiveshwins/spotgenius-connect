import logging
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response, JSONResponse
from sqlalchemy import func, cast, Float
from sqlalchemy.orm import Session, aliased
from app.models import base
from app.models.push_payment import PushPayment
from app.schema.push_payment_schema import PushPaymentSchema
from app.dependencies.deps import get_db
from app.service.auth_service import AuthService
from app.service import session_manager
from app import schema, config
from app.utils import enum
import requests
from app.utils.common import DateTimeUtils


logger = logging.getLogger(__name__)


subscribe_api = APIRouter()


@subscribe_api.post("/v1/subscribe/sg")
def subscribe_sg(
    data: Dict,
    db: Session = Depends(get_db)
):
    """
    Receive Subscribed Events from SG-Admin
    """
    logger.debug({k: v for k, v in data.items()
                  if k not in {'spot_update_image_base64', 'vehicle_crop_image_base64'}})

    # logger.debug(data)
    # if image:
    #     logger.debug(f"image name: {image.filename}")

    if data.get('challenge_key'):
        return data['challenge_key']

    try:
        if data.get('event_key') == enum.Event.parking_spot_updates.value:
            sg_event_schema = schema.SgAnprEventSchema(**data)
            logger.debug(f'Event received for spot {sg_event_schema.parking_spot_name}')
            logger.debug(f'Event: {sg_event_schema.event_key} / '
                         f'Spot: {sg_event_schema.parking_spot_name} - Event Received)')
        else:
            data.update(event_key=enum.Event[data.get('event_key')].value)
            sg_event_schema = schema.SgAnprEventSchema(**data)
            logger.debug(f'Event received with plate number {sg_event_schema.license_plate}')
            logger.debug(f'Event: {sg_event_schema.event_key} / LPR: {sg_event_schema.license_plate} - Event Received)')

        # Convert date time format for Plate Recognizer camera
        sg_event_schema.entry_time = DateTimeUtils.parse_datetime_and_convert(sg_event_schema.entry_time, "%Y-%m-%dT%H:%M:%S")
        sg_event_schema.exit_time = DateTimeUtils.parse_datetime_and_convert(sg_event_schema.exit_time, "%Y-%m-%dT%H:%M:%S")
        sg_event_schema.timestamp = DateTimeUtils.parse_datetime_and_convert(sg_event_schema.timestamp, "%Y-%m-%dT%H:%M:%S")

        response_message = session_manager.SessionManager.create_session_audit(db, sg_event_schema)
        logger.debug(f"Event execute response: {response_message}")
        return JSONResponse(content={"message": response_message}, status_code=200)

    except Exception as e:
        logger.critical(f"Request Error: {str(e)}")


@subscribe_api.post("/v1/subscribe/arrive")
def subscribe_arrive(data: Dict, db: Session = Depends(get_db),
                     auth_token: str = Depends(AuthService.verify_basic_auth)):
    """
    Receive Arrive Payment Provider Pushed Data
    """
    logger.info(f"Push payment event received with request {data}")
    resource_data = data.get('resource')
    provider_creds = (db.query(base.ProviderCreds)
                      .filter(base.ProviderCreds.text_key == 'provider.payment.arrive').first())

    plate_number = resource_data.get('license_plate')
    push_payment_schema = PushPaymentSchema(
        start_date_time=resource_data.get('start_date_time'),
        end_date_time=resource_data.get('end_date_time'),
        price_paid=resource_data.get('price_paid').get('USD'),
        plate_number=plate_number.lower() if plate_number else None,
        spot_id=resource_data.get('space_identifier'),
        original_response=str(resource_data),
        provider_id=provider_creds.provider_id,
        external_reference_id=resource_data.get('resource_id'),
        location_id=resource_data.get('location_id')
    )
    PushPayment.create(db, push_payment_schema)
    logger.info(f"Push payment processed successfully for plate: {plate_number}")
    return Response(status_code=204)


@subscribe_api.get("/v1/set_total")
def set_total_amount_paid(db: Session = Depends(get_db)):
    alias_session_log = aliased(base.SessionLog)

    paid_amount_subquery = (
        db.query(
            alias_session_log.session_id.label('session_id'),
            func.sum(cast(func.json_extract_path_text(alias_session_log.meta_info, 'price_paid'), Float)).label(
                'total_paid')
        )
        .filter(alias_session_log.action_type == "Paid")
        .group_by(alias_session_log.session_id)
        .subquery()
    )

    update_query = (
        db.query(base.Sessions.id, paid_amount_subquery.c.total_paid)
        .join(paid_amount_subquery, base.Sessions.id == paid_amount_subquery.c.session_id)
    )

    for session_id, total_paid in update_query:
        db.query(base.Sessions).filter(base.Sessions.id == session_id).update({"total_paid_amount": total_paid})

    db.commit()


@subscribe_api.post("/v1/subscribe/tiba/npa")
def subscribe_tiba_npa(data: Dict, db: Session = Depends(get_db)):
    """
    Receive Tiba NPA Pushed Data
    """
    import json

    logger.debug(data)
    if data.get('challenge_key'):
        return data['challenge_key']
    global sg_event_schema
    try:
        if data.get('event_key') == enum.Event.parking_spot_updates.value:
            logger.info(f'TIBA {data.get("spot_status")} event came')
            sg_event_schema = schema.SgAnprEventSchema(**data)
            logger.debug(f'Event: {sg_event_schema.event_key} / '
                         f'Spot Status: {sg_event_schema.spot_status} / '
                         f'Spot: {sg_event_schema.parking_spot_name} - Event Received)')

            # set actual value based on spot status
            if sg_event_schema.spot_status == enum.Event.unavailable.name:
                actualValue = 1
            elif sg_event_schema.spot_status == enum.Event.available.name:
                actualValue = 0
        else:
            logger.debug(f'Event: {sg_event_schema.event_key} / LPR: {sg_event_schema.license_plate} - Event Received)')
            return

        login_url = config.settings.TIBA_NPA_API_HOST + "/janus-integration/api/ext/login"
        login_payload = json.dumps({
                "username": config.settings.TIBA_NPA_API_USERNAME,
                "password": config.settings.TIBA_NPA_API_PASSWORD
            })
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        login_response = requests.post(login_url, data=login_payload, headers=headers)

        if login_response and login_response.status_code == 200:
            login_response = login_response.json()
            
            token = login_response.get('item')['token']['value']
            headers.update({
                "Janus-TP-Authorization": token
            })

            data = json.dumps({
                "counterId": config.settings.TIBA_NPA_API_COUNTERID,
                "actualValue": actualValue,
                "reason": config.settings.TIBA_NPA_API_REASON,
                "adjustment": config.settings.TIBA_NPA_API_ADJUSTMENT
            })
            
            update_counter_url = config.settings.TIBA_NPA_API_HOST + "/janus-integration/api/ext/counter/update"
            logger.info(f'counter update API called with request / {data}')
            response = requests.put(update_counter_url, data=data, headers=headers)
            logger.info(f'Counter update API response {response.json()}')
            return response.json()

    except Exception as e:
        logger.critical(f"Request Error: {str(e)}")


@subscribe_api.post('/v1/subscribe/data-ticket')
def subscribe_data_ticket(data: dict,
                          auth_token: str = Depends(AuthService.verify_api_key_data_ticket),
                          db: Session = Depends(get_db)):
    try:
        # Extract necessary data from the incoming request
        print("incoming request: ", data)
        plate_number = data.get("plate_number")
        provider_id = data.get("provider_id")
        response_data = data
        ticket_number = data.get("ticket_number")

        # Insert the enforcement response into the database
        new_response = base.EnforcementResponseStore.insert_enforcement_response(
            db=db,
            plate_number=plate_number,
            provider_id=provider_id,
            response_data=response_data,
            ticket_number=ticket_number
        )

        if new_response:
            return {"message": "data saved successfully", "id": new_response.id}
        else:
            raise HTTPException(status_code=500, detail="Failed to store enforcement response")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
