import logging
from typing import Optional, Union

from fastapi import APIRouter, Query
from fastapi import Response
from datetime import datetime, timedelta
import json
from sqlalchemy.orm import Session

from fastapi.params import Depends
from app.config import redis_client
from app.models import base
from app.dependencies.deps import get_db

demo_lot_api = APIRouter()


logger = logging.getLogger(__name__)

@demo_lot_api.get('/v1/payment/provider/{provider_id}/{plate_number}')
def check_payment(plate_number: str,
                  provider_id: int,
                  request_flag: Optional[int] = Query(None),
                  db: Session = Depends(get_db)
                  ):
    response = None

    provider = base.Provider.get_provider_by_id(db, provider_id)
    demo_configuration = provider.meta_data.get("demo_configuration", {})
    lpr = demo_configuration.get("lpr", {})
    payment_time_frame = demo_configuration.get("payment_time_frame", {})

    logger.info(f"Checking Payment with demo lot api for plate_number: {plate_number}")
    current_time = datetime.utcnow()
    plate_responses = {
        lpr.get('demo_no_payment_lpr'): {},
        lpr.get('demo_one_time_payment_lpr'): {
            "price_paid": "10",
            "start_date_time": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_date_time": (current_time + timedelta(minutes=payment_time_frame.get("demo_one_time", 5))).strftime("%Y-%m-%d %H:%M:%S"),
            "full_price": "15",
            "location_name": "",
            "plate_number": f"{plate_number}",
            "action_type": "Paid"
        },
        lpr.get('demo_multiple_time_payment_lpr'):{
            "not_paid": {},
            "paid": {
            "price_paid": "10",
            "start_date_time": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_date_time": (current_time + timedelta(minutes=payment_time_frame.get("demo_multiple_time", 10))).strftime("%Y-%m-%d %H:%M:%S"),
            "station_price": "15",
            "location_name": "",
            "plate_number": f"{plate_number}",
            "action_type": "Paid"
        }
        }
    }

    # Check for the plate number and return the corresponding response
    if plate_number in plate_responses:
        if plate_number == lpr.get('demo_no_payment_lpr'):
            response_data = plate_responses[plate_number]
            response = Response(content=json.dumps(response_data), status_code=200, media_type="application/json")

        elif plate_number == lpr.get('demo_one_time_payment_lpr'):
            response_data = plate_responses[plate_number]
            response = Response(content=json.dumps(response_data), status_code=200, media_type="application/json")

        elif plate_number == lpr.get('demo_multiple_time_payment_lpr'):

            if request_flag == 1:
                logger.debug(f"Payment found in second check plate_number: {plate_number}")
                response_data = plate_responses[plate_number]["not_paid"]

            else:
                response_data = plate_responses[plate_number]["paid"]
            response = Response(content=json.dumps(response_data), status_code=200, media_type="application/json")

    return response
