import logging

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app import schema
from app.dependencies.deps import get_db
from app.models import base
from app.utils import enum
from app.utils.common import api_response
from app.utils.common import attach_admin_fake_provider, detach_admin_fake_provider, get_connected_provider, \
    convert_utc_time_to_specific_timezone, convert_max_park_time_to_hour_minutes, default_connection_sg_admin
from app.utils.common import convert_max_park_time_to_minutes
from app.utils.parking_api import ParkingAPI
from app.utils.security import verify_token

logger = logging.getLogger(__name__)
parking_router = APIRouter()


@parking_router.post('/v1/parking_lot/{parking_lot_id}/parking_timing')
def set_parking_timing(
    parking_lot_id: int,
    parking_timing_schema: schema.ParkingTimingSchema,
    organization: str = Header(...),
    # token: base.User = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Set parking timing
    """
    try:
        # get the created or updated organization
        organization = ParkingAPI.create_or_update_organization(db, organization, parking_timing_schema.organization_name)

        # get the created or updated parking lot
        connect_parkinglot = ParkingAPI.create_or_update_parkinglot(db, parking_lot_id, organization.id, parking_timing_schema)

        # connect sg-admin provider
        default_connection_sg_admin(db, connect_parkinglot.id)

        # detach fake provider when there is no free window
        if parking_timing_schema.parking_operations == enum.ParkingOperations.paid_24_hours.value or parking_timing_schema.parking_operations == enum.ParkingOperations.spot_based_24_hours_free_parking.value:
            detach_admin_fake_provider(db, connect_parkinglot.id)
        else:
            # attach admin fake provider if no other providers are connected
            connected_providers = get_connected_provider(db, enum.ProviderTypes.PROVIDER_FAKE.value, [connect_parkinglot.id])
            if not connected_providers:
                attach_admin_fake_provider(db, connect_parkinglot.id)

        # update parking timing
        ParkingAPI.update_parking_timing(db, parking_timing_schema, connect_parkinglot)

        # update event type for overstay violation when payment window not always paid parking
        # ParkingAPI.ConfigureOverstayViolationEventType(db, connect_parkinglot, parking_timing_schema.parking_operations)
        db.commit()

        ParkingAPI.upsert_violation_config(connect_parkinglot, organization, parking_timing_schema)

        return api_response(
                message="Successfully saved.",
                status="success",
                data=[],
                status_code=200)

    except Exception as e:
        logger.error(f"Error: {e}")
        return api_response(
            message="An error occurred while setting not paid parking timing.",
            status="error",
            data={"error": str(e)},
            status_code=500
        )


@parking_router.get('/v1/parking_lot/{parking_lot_id}/parking_timing')
def get_parking_timing(parking_lot_id: int,
                                timezone: str = None,
                                token: base.User = Depends(verify_token),
                                db: Session = Depends(get_db)):
    """
    Get parking timing
    """
    try:
        connect_parkinglot = base.ConnectParkinglot.get(db, parking_lot_id)
        if not connect_parkinglot:
            return api_response(
                message="Parking lot not found.",
                status="error",
                data=[],
                status_code=404
            )

        parking_time_slots = base.ParkingTime.get_records_order_by_id(db, connect_parkinglot.id)
        parking_timeframes = []
        for parking_time_slot in parking_time_slots:
            start_time = convert_utc_time_to_specific_timezone(parking_time_slot.start_time, timezone, '%H:%M')
            end_time = convert_utc_time_to_specific_timezone(parking_time_slot.end_time, timezone, '%H:%M')

            parking_timeframes.append(
                schema.ParkingTimeframes(
                    start_time = start_time,
                    end_time= end_time,
                    id = parking_time_slot.id
                )
            )

        max_park_time = convert_max_park_time_to_hour_minutes(connect_parkinglot.maximum_park_time_in_minutes)

        data = schema.ParkingTimeResponseSchema(
            isProviderConnected = base.ConnectParkinglot.is_payment_and_reservation_provider_configured(db, parking_lot_id=parking_lot_id),
            parking_operations = connect_parkinglot.parking_operations,
            max_park_time = schema.MaximumParkTime(
                hours = max_park_time["hours"],
                minutes = max_park_time["minutes"]
            ),
            parking_timeframes=parking_timeframes
        )

        return api_response(
            message="Successfully retrieved.",
            status="success",
            data=data.dict(),
            status_code=200)
    except Exception as e:
        logger.error(f"Error: {e}")
        return api_response(
            message="An error occurred while setting not paid parking timing.",
            status="error",
            data={"error": str(e)},
            status_code=500
        )


@parking_router.patch('/v1/sessions/delete')
def delete_sessions(session_delete_schema: schema.SessionsDeleteSchema,
                    token: base.User = Depends(verify_token),
                    db: Session = Depends(get_db)):
    try:
        connect_parkinglot = base.ConnectParkinglot.get(db, session_delete_schema.parking_lot_id)
        if not connect_parkinglot:
            return api_response(
                message="Parking lot not found.",
                status="error",
                data=[],
                status_code=404
            )
        base.Sessions.soft_delete_sessions(db, session_delete_schema.parking_lot_id, session_delete_schema.delete_from_datetime)
        return api_response(
            message="Successfully deleted.",
            status="success",
            data={},
            status_code=200)
    except Exception as e:
        logger.error(f"Error: {e}")
        return api_response(
            message="An error occurred while deleting sessions.",
            status="error",
            data={"error": str(e)},
            status_code=500
        )
