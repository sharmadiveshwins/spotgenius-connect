import logging

import pytz
from datetime import datetime
from dateutil import parser, tz
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.dependencies.deps import get_db
from app.service.session_manager import SessionManager
from typing import List
from app.schema import ProviderSchema
from app.models import base
from app.utils.common import api_response
from app.service.configure_lot_service import ConfigureLot

logger = logging.getLogger(__name__)

audit_events_router = APIRouter()


@audit_events_router.get("/v1/audit/events", response_model=dict)
def get_event_sessions(start_date_time: str = None,
                       end_date_time: str = None,
                       parking_lot_id: int = None,
                       db: Session = Depends(get_db),
                       timezone: str = None):
    if start_date_time:
        start_date_time_naive = parser.parse(start_date_time)
        if start_date_time_naive.tzinfo is None:
            start_date_time_naive = pytz.utc.localize(start_date_time_naive)
    else:
        start_date_time_naive = datetime.now(pytz.utc)

    if end_date_time:
        end_date_time_naive = parser.parse(end_date_time)
        if end_date_time_naive.tzinfo is None:
            end_date_time_naive = pytz.utc.localize(end_date_time_naive)
    else:
        end_date_time_naive = datetime.now(pytz.utc)

    start_date_time = start_date_time_naive.astimezone(pytz.utc)
    end_date_time = end_date_time_naive.astimezone(pytz.utc)

    return SessionManager.fetch_session(db,
                                        parking_lot_id,
                                        start_date_time,
                                        end_date_time).dict()


@audit_events_router.get("/v2/audit/events", response_model=dict)
def get_event_sessions(start_date_time: str = None,
                       end_date_time: str = None,
                       parking_lot_id: int = None,
                       db: Session = Depends(get_db),
                       page_number: int = None,
                       page_size: int = None,
                       time_frame: str = 'date',
                       session_type: str = None,
                       provider: str = None,
                       plate_number_or_spot: str = None,
                       timezone: str = None):

    if start_date_time:
        start_date_time_naive = parser.parse(start_date_time)
        if start_date_time_naive.tzinfo is None:
            start_date_time_naive = pytz.utc.localize(start_date_time_naive)
    else:
        start_date_time_naive = datetime.now(pytz.utc)

    if end_date_time:
        end_date_time_naive = parser.parse(end_date_time)
        if end_date_time_naive.tzinfo is None:
            end_date_time_naive = pytz.utc.localize(end_date_time_naive)
    else:
        end_date_time_naive = datetime.now(pytz.utc)

    start_date_time = start_date_time_naive.astimezone(pytz.utc)
    end_date_time = end_date_time_naive.astimezone(pytz.utc)

    return SessionManager.fetch_session_v3(db,
                                           parking_lot_id,
                                           start_date_time,
                                           end_date_time,
                                           page_number,
                                           page_size,
                                           session_type,
                                           provider,
                                           plate_number_or_spot,
                                           time_frame
                                           ).dict()


@audit_events_router.get(
    '/v1/get-parking-lot-providers/{parking_lot_id}', 
    response_model=List[ProviderSchema]
)
def get_providers(
    parking_lot_id: int,
    provider_type: str,
    db: Session = Depends(get_db),
):
    lot = base.ConnectParkinglot.get_parking_lot(db, parking_lot_id)
    if not lot:
        return api_response(
            message=f'parking lot is not register with id {parking_lot_id}',
            status="success",
            data=[]
        )

    connected_providers = ConfigureLot.get_lot_providers(db, lot.id, provider_type)

    return api_response(
        message="Successfully retrieved.",
        status="success",
        data=connected_providers
    )
