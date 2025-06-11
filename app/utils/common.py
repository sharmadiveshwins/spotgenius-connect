import copy
import json
import logging
import requests
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Union, Optional
from urllib.parse import quote

from fastapi.responses import JSONResponse

import pytz
from dateutil import parser

from app import schema
from app.config import settings
from app.models import base
from app.models.connect_parkinglot import ConnectParkinglot
from app.models.provider_creds import ProviderCreds
from app.service.event_service import EventService
from app.utils import enum
from app.utils.image_utils import ImageUtils
from sqlalchemy.orm import Session
from sqlalchemy import func
import time

logger = logging.getLogger(__name__)


class DateTimeUtils:

    @staticmethod
    def is_future_date(date_str):
        result = False

        try:
            if date_str.strip():

                given_date = parser.parse(date_str)
                # Ensure the parsed date is in UTC if not already
                if given_date.tzinfo is None:
                    given_date = given_date.replace(tzinfo=timezone.utc)

                current_utc_datetime = datetime.now(timezone.utc)
                result = given_date > current_utc_datetime
        except Exception as e:
            logger.critical(f"Exception: {str(e)}")
        return result

    @staticmethod
    def calculate_time_difference(end_date, start_date):

        start_date = parser.parse(start_date).astimezone(pytz.UTC)
        expiry_date = parser.parse(end_date).astimezone(pytz.UTC)

        time_difference_seconds = (expiry_date - start_date).total_seconds()
        total_hours = int(time_difference_seconds // 3600)
        remaining_minutes = round((time_difference_seconds % 3600) / 60)
        if total_hours > 0 and remaining_minutes == 60:
            total_hours += 1
            time_difference_formatted = f"{total_hours} hr"
        elif total_hours > 0 and remaining_minutes != 60:
            time_difference_formatted = f"{total_hours}.{remaining_minutes} hr"
        else:
            time_difference_formatted = f"{remaining_minutes} min"

        return time_difference_formatted

    @staticmethod
    def get_overstay_time(start_date: datetime, end_date: datetime):
        time_difference = int((end_date - start_date).total_seconds() / 60)
        c = (datetime.utcnow() - start_date).total_seconds() / 60
        over_stay = c - time_difference
        return over_stay

    @staticmethod
    def convert_to_iso_format(date_str):
        if date_str is None:
            return date_str

        # List of possible date formats
        date_formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%d-%m-%YT%H:%M:%S',
            '%Y/%m/%d %H:%M:%S',
            '%d-%m-%Y %H:%M:%S',
            '%d/%m/%Y %H:%M:%S',
            '%d-%b-%Y %H:%M:%S',
            '%d %b %Y %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y%m%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f'
        ]

        # If the date string has a 'Z' at the end (UTC time), remove it for parsing
        if date_str.endswith('Z'):
            date_str = date_str[:-1]

        # Check if there's an extra digit in the fractional seconds
        if '.' in date_str:
            date_str = date_str.split('.')[0] + '.' + date_str.split('.')[1][:6]  # Truncate to 6 digits if needed

        for date_format in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, date_format)
                return parsed_date.strftime('%Y-%m-%dT%H:%M:%S')
            except ValueError:
                continue

        return date_str

    @staticmethod
    def get_utc_timestamp():
        # Return the current UTC time as a string in "YYYY-MM-DD HH:MM:SS" format
        return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def parse_datetime_and_convert(time, format):
        if time is None:
            return time

        time_str = time.strftime(format)
        return datetime.strptime(time_str, format)


def next_at_for_task(event, parking_connect_obj, timestamp, payment_window):
    if timestamp is not None:
        return timestamp

    event_timestamp = event.timestamp

    grace_period = parking_connect_obj.grace_period
    if event.spot_payment_grace_period and event.license_plate is None:
        grace_period = event.spot_payment_grace_period
    # elif event.zone_payment_grace_period:
    #     grace_period = event.zone_payment_grace_period

    # Default case if no specific condition matches
    next_at = (
            event_timestamp + timedelta(minutes=grace_period)
            if payment_window['status']
            else event_timestamp
        )
    return next_at


def api_response(*, message: str, status: str,
                 data: Union[List[Any], Dict[str, Any], None] = None,
                 status_code: Optional[int] = 200) -> Dict[str, Any]:
    response_data = {
        "message": message,
        "status": status,
        "data": data if data is not None else []
    }
    return JSONResponse(content=response_data, status_code=status_code)


def update_without_replacement(target_dict, update_dict):
    for key, value in update_dict.items():
        if key not in target_dict:
            target_dict[key] = value
    return target_dict


def custom_encoder(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def split_first_dot(text):
    parts = text.split('.', 1)  # Split at the first dot
    if len(parts) > 1:
        return parts[0], parts[1]
    else:
        return text  # Return the single value if no dot is found

# TODO
# need enhancement in below function
def format_params(param: dict):
    if param['type'] == 'timestamp' and 'format' in param:
        try:
            date_obj = datetime.strptime(param['value'], "%Y-%m-%dT%H:%M:%S")
        except:
            date_obj = datetime.strptime(param['value'], "%Y-%m-%d %H:%M:%S.%f")

        if 'operation' in param and 'key' in param['operation']:
            if param['operation']['operator'] == enum.Operators.ADD.value:
                date_obj = date_obj + timedelta(**{param['operation']['key']: param['operation']['value']})
            if param['operation']['operator'] == enum.Operators.SUBTRACT.value:
                date_obj = date_obj - timedelta(**{param['operation']['key']: param['operation']['value']})

        param['value'] = date_obj.strftime(param['format'])

    if param['type'] == 'timestamp':
        if 'operation' in param:
            if "time" in param['operation'] and "format" in param['operation']:
                date_str = f"{param['value']} {param['operation']['time']}"  # Extract `HH:MM:SS` part
                date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S%z")
                formatted_date = date_obj.strftime("%Y-%m-%d %H:%M:%S%z")
                url_encoded_date = quote(formatted_date, safe="")
                param['value'] = url_encoded_date

    return param['value']


def find_key_in_dict(data, target_key):
    if isinstance(data, dict):
        if target_key in data:
            return data[target_key]
        for key, value in data.items():
            result = find_key_in_dict(value, target_key)
            if result is not None:
                return result
    elif isinstance(data, list):
        for item in data:
            result = find_key_in_dict(item, target_key)
            if result is not None:
                return result
    return None


# car_identification for dynamically showing logs for LPR or Spot based
def car_identification_log(task):
    car_identification = f'LPR: {task.plate_number}' if task.plate_number else f'SPOT: {task.parking_spot_id}'
    return car_identification


def build_task_from_event(db, task: base.Task, timestamp):
    session_by_id = base.Sessions.get_session_by_id(db, task.session_id)
    str_to_dict = session_by_id.entry_event if isinstance(session_by_id.entry_event, dict) else json.loads(session_by_id.entry_event)
    anpr_event_schema = schema.SgAnprEventSchema(**str_to_dict)
    attributes = {
        "session_id": session_by_id.id,
        "sgadmin_alerts_ids": task.sgadmin_alerts_ids,
        "parking_spot_name": session_by_id.parking_spot_name,
        "parking_spot_id": session_by_id.spot_id,
        "request_flag": 1
    }
    for attr, value in attributes.items():
        setattr(anpr_event_schema, attr, value)
    EventService.execute_event(events=[anpr_event_schema], db=db, timestamp=timestamp)


def set_text_for_session_ui(has_reservation, is_waiting_for_payment):
    if has_reservation or is_waiting_for_payment:
        return "waiting for grace period"
    else:
        return None
    # if has_reservation and not is_waiting_for_payment:
    #     return "waiting for reservation"
    # elif not has_reservation and is_waiting_for_payment:
    #     return "waiting for payment"
    # elif has_reservation and is_waiting_for_payment:
    #     return "waiting for payment/reservation"
    # else:
    #     return None


def configure_alert_body(session_by_id, task):

    description = ""
    spot_name, plate_number = session_by_id.parking_spot_name, session_by_id.lpr_number
    # Define the event type descriptions
    event_type_descriptions = {
        enum.EventTypes.PAYMENT_VIOLATION.value: {
            "spot": f"Payment violation has been detected for the vehicle" + (f" on spot {spot_name}." if spot_name else "."),
            "plate": f"Payment violation has been detected for the vehicle with the plate number {plate_number}."
        },
        enum.EventTypes.OVERSTAY_VIOLATION.value: {
            "spot": f"Overstay violation has been detected for the vehicle"+ (f" on spot {spot_name}." if spot_name else "."),
            "plate": f"Overstay violation has been detected for the vehicle with the plate number {plate_number}."
        }
    }

    if task.parking_spot_id:
        description = event_type_descriptions.get(task.event_type, {}).get("spot", "")
    elif task.plate_number:
        description = event_type_descriptions.get(task.event_type, {}).get("plate", "")

    details = {
        enum.Feature.PAYMENT_CHECK_LPR.value: f"Payment violation has been detected for the vehicle with the plate number {session_by_id.lpr_number}",
        enum.Feature.PAYMENT_CHECK_SPOT.value: f"Payment violation has been detected for the vehicle on spot {session_by_id.parking_spot_name}.",
        enum.Feature.NOTIFY_SG_ADMIN.value: description
    }

    # images_urls = [task.sg_event_response.get('frame_image_url', ''),
    #                task.sg_event_response.get('vehicle_crop_image_url', ''),
    #                task.sg_event_response.get('lpr_crop_image_url', '')]

    alert_body = {
        # change title from Parking Spot Time Exceeded to Parking Time Exceeded
        "title": "Payment Violation" if task.event_type == "payment.violation" else "Parking Time Exceeded",
        "severity": "high" if task.event_type == "payment.violation" else "medium",
        "category": "violation",
        "subcategory": "Non Payment" if task.event_type == "payment.violation" else "Overstay",
        "alert_type": "info",
        "alert_type_id": 39 if task.event_type == enum.EventTypes.PAYMENT_VIOLATION.value else 2,
        "parking_lot_id": task.parking_lot_id,
        # "image_base64s": [ImageUtils.image_url_to_base64(image_url) for image_url in images_urls if image_url] if images_urls else '',
        "details": details.get(task.feature_text_key, ""),
        "license_plate_number": task.plate_number,
        "parking_spot_id": task.parking_spot_id if task.parking_spot_id else None,
        "alert_state": "open",
        "alert_trigger_state": "active",
        "entity_name": "sgconnect",
        "include_image": True if task.parking_spot_id else False,
        "vehicle_parking_usage_anpr_record_id": task.sg_event_response.get("vehicle_record_id", None),
        "parking_history_id": task.sg_event_response.get("history_id", None)
    }

    return alert_body


def execute_violation_before_exit(db, task):
    from app.service import TaskService
    TaskService.process_violation_task(db, task)


def default_connection_sg_admin(db, parking_lot_id):
    creds__filter = db.query(ProviderCreds).filter(ProviderCreds.text_key == enum.Provider.PROVIDER_ENFORCEMENT_ADMIN.value).first()

    if creds__filter:
        provider_connect_obj = db.query(base.ProviderConnect).filter(base.ProviderConnect.provider_creds_id == creds__filter.id,
                                                             base.ProviderConnect.connect_id == parking_lot_id).first()
        if not provider_connect_obj:
            provider_connect_obj = base.ProviderConnect.insert(db=db,
                                                            connect_id=parking_lot_id,
                                                            provider_creds_id=creds__filter.id,
                                                            facility_id=enum.DefaultFacilityCode.ADMIN.value
                                                            )

    # get credentials
    admin__id = db.query(base.Provider).filter(base.Provider.name == "Admin").first().id
    # get feature url
    feature_url_path_id = db.query(base.FeatureUrlPath).filter(
        base.FeatureUrlPath.provider_id == admin__id).first().id
    # get feature id
    feature_id = db.query(base.Feature).filter(
            base.Feature.text_key == enum.Feature.NOTIFY_SG_ADMIN.value).first().id
    # get parking lot provider feature
    parking_lot_provider_feature_obj = base.ParkinglotProviderFeature.get_by_provider_connect_and_feature(db, provider_connect_obj.id, feature_id)
    if not parking_lot_provider_feature_obj:
        parking_lot_provider_feature = schema.ParkinglotProviderFeatureCreateSchema(
            provider_connect_id=provider_connect_obj.id,
            feature_id=feature_id)

        parking_lot_provider_feature_obj = base.ParkinglotProviderFeature.create(db, parking_lot_provider_feature)

    parkinglot = base.ConnectParkinglot.get_by_id(db, parking_lot_id=parking_lot_id)


    removable_event_keys = []
    if parkinglot.parking_operations == enum.ParkingOperations.specify_lpr_based_paid_parking_time.value:
        events_keys = base.EventTypes.get_events_by_text_key(db, [enum.EventTypes.PAYMENT_VIOLATION.value,
                                                                  enum.EventTypes.OVERSTAY_VIOLATION.value])

    elif parkinglot.parking_operations == enum.ParkingOperations.paid_24_hours.value:
        events_keys = base.EventTypes.get_events_by_text_key(db, [enum.EventTypes.PAYMENT_VIOLATION.value])
        removable_event_keys = base.EventTypes.get_events_by_text_key(db, [enum.EventTypes.OVERSTAY_VIOLATION.value])

    elif parkinglot.parking_operations == enum.ParkingOperations.lpr_based_24_hours_free_parking.value:
        events_keys = base.EventTypes.get_events_by_text_key(db, [enum.EventTypes.OVERSTAY_VIOLATION.value])
        removable_event_keys = base.EventTypes.get_events_by_text_key(db, [enum.EventTypes.PAYMENT_VIOLATION.value])

    else:
        events_keys = base.EventTypes.get_events_by_text_key(db, [enum.EventTypes.PAYMENT_VIOLATION.value])
        removable_event_keys = base.EventTypes.get_events_by_text_key(db, [enum.EventTypes.OVERSTAY_VIOLATION.value])

    for event in events_keys:
        feature_event_type = base.FeatureEventType.get_attached_feature_event_type(db, event.id, feature_url_path_id, parking_lot_provider_feature_obj.id)
        if not feature_event_type:
            feature_event_schema = schema.FeatureEventType(
                event_type_id=event.id,
                feature_url_path_id=feature_url_path_id,
                parkinglot_provider_feature_id=parking_lot_provider_feature_obj.id
            ).exclude_key(['provider_id'])

            base.FeatureEventType.create(db, feature_event_schema)

    # remove extra attached event type
    for removable_event in removable_event_keys:
        base.FeatureEventType.delete_attached_feature_event_type(db, removable_event.id, feature_url_path_id, parking_lot_provider_feature_obj.id)

    return


def format_body(body_to_format):

    result_dict = {}

    for body_data in body_to_format:
        key = body_data['key']
        value = body_data['value']
        if key == "Timestamp":
            value = DateTimeUtils.get_utc_timestamp()
        # Add or update the key-value pair in the dictionary
        result_dict[key] = value

    return result_dict


def extract_record_id(data):
    # Extract the message from the dictionary
    message = data.get("Message", "")
    success = data.get("Success", False)
    # Use regex to find the integer in the message
    match = re.search(r'\d+', message)
    # Return the integer if found, otherwise return None
    return {
        "id": int(match.group()) if match else None,
        "Success": success
    }


def attach_admin_fake_provider(db, parking_lot_id):
    """
    Attach Admin Fake Provider
    """
    provider = db.query(base.Provider).filter(base.Provider.name == "Admin Fake").first()
    if provider:
        provider_creds = db.query(ProviderCreds).filter(ProviderCreds.provider_id == provider.id).first()
        if provider_creds:
            create_provider_connect_schema = schema.CreateProviderConnectSchema(
                connect_id=parking_lot_id,
                provider_creds_id=provider_creds.id,
                facility_id='Admin fake'
            )
            provider_connect_obj = base.ProviderConnect.create(db, create_provider_connect_schema)
            # payment.check.lpr
            feature = base.Feature.get_by_text_key(db, 'payment.check.lpr')
            parking_lot_provider_feature_obj = base.ParkinglotProviderFeature.create_parkinglot_provider_feature(db, schema.ParkinglotProviderFeatureCreateSchema(
                provider_connect_id=provider_connect_obj.id,
                feature_id=feature.id
            ))
            base.FeatureEventType.create_feature_event_type(db, schema.CreateFeatureEventType(
                event_type_id=db.query(base.EventTypes).filter(base.EventTypes.text_key == 'car.entry').first().id,
                feature_url_path_id=db.query(base.FeatureUrlPath).filter(base.FeatureUrlPath.provider_id == provider.id).first().id,
                parkinglot_provider_feature_id=parking_lot_provider_feature_obj.id
            ))


def detach_admin_fake_provider(db, parking_lot_id):
    """
    Detach Admin Fake Provider
    """
    # provider = db.query(base.Provider).filter(base.Provider.name == "Admin Fake").first()
    provider = base.Provider.get_provider_by_provider_type(db, enum.ProviderTypes.PROVIDER_FAKE.value)
    if provider:
        provider_creds = db.query(ProviderCreds).filter(ProviderCreds.provider_id == provider.id).first()
        base.ProviderConnect.detach_parking_lot(db, provider_creds.id, parking_lot_id)


def get_connected_provider(db: Session, filter_by: str, parking_lot_ids: List[int]):
    results = (
        db.query(
            base.ProviderConnect.provider_creds_id,
            base.ProviderCreds.provider_id,
            base.Feature.text_key,
            func.count(func.distinct(base.ProviderConnect.connect_id, base.ProviderConnect.provider_creds_id)).label('connected_provider_count'),

        )
        .join(base.ProviderCreds, base.ProviderConnect.provider_creds_id == base.ProviderCreds.id)
        .join(base.Provider, base.ProviderCreds.provider_id == base.Provider.id)
        .join(base.ProviderTypes, base.Provider.provider_type_id == base.ProviderTypes.id)
        .join(base.ParkinglotProviderFeature,
              base.ProviderConnect.id == base.ParkinglotProviderFeature.provider_connect_id)
        .join(base.Feature,
              base.Feature.id == base.ParkinglotProviderFeature.feature_id)
        .join(base.FeatureEventType,
              base.ParkinglotProviderFeature.id == base.FeatureEventType.parkinglot_provider_feature_id)
        .filter(base.ProviderConnect.connect_id.in_(parking_lot_ids))
        .filter(base.ProviderTypes.text_key == filter_by)
        .group_by(base.ProviderConnect.provider_creds_id,
                  base.ProviderCreds.provider_id,
                  base.Feature.text_key,
                  base.Provider.id
                  )
        .all()
    )
    return results


def sanitize_logged_data(data, keys_to_exclude):
    if isinstance(data, str):
        data = json.loads(data)

    sanitized_data = copy.deepcopy(data)  # Create a deep copy to avoid modifying the original data

    keys_to_truncate = {"LRPlateImage", "LRContextImage", "LPROverviewImage", "FRContextImage", "FROverviewImage", "FRPlateImage"}

    for key in keys_to_exclude:
        # Remove keys specified in keys_to_exclude
        if sanitized_data and key in sanitized_data:
            sanitized_data.pop(key, None)

    for key in keys_to_truncate:
        # Truncate the value of specified keys to 10 words
        if sanitized_data and key in sanitized_data:
            value = sanitized_data.get(key, "")
            if isinstance(value, str):
                truncated_value = value[:20]
                sanitized_data[key] = truncated_value

    return json.dumps(sanitized_data)


def convert_time_to_utc_by_timezone(time: str, timezone: str, format: str):
    time_obj = datetime.strptime(time, format).time()
    today = datetime.now().date()
    local_tz = pytz.timezone(timezone)

    date_time = datetime.combine(today, time_obj)
    utc_date_time = local_tz.localize(date_time).astimezone(pytz.utc)

    return utc_date_time.strftime(format)


def convert_utc_time_to_specific_timezone(time: str, timezone: str, format: str):
    datetime_obj = datetime.combine(datetime.today(), time)
    utc_time = datetime_obj.replace(tzinfo=pytz.utc)
    converted_time = utc_time.astimezone(pytz.timezone(timezone)).time()

    return converted_time.strftime(format)


def parkinglot_overstay_limit(connect_parkinglot, current_time:datetime):
    overstay_time = None
    maximum_park_time = connect_parkinglot.maximum_park_time_in_minutes

    if connect_parkinglot.parking_operations != enum.ParkingOperations.paid_24_hours.value and connect_parkinglot.parking_operations != enum.ParkingOperations.spot_based_24_hours_free_parking.value and maximum_park_time is not None and maximum_park_time >= 0:
        overstay_time = timedelta(minutes=maximum_park_time)

    return overstay_time


def convert_max_park_time_to_minutes(max_park_time):
    """
    Convert hours and minutes to total minutes.
    """
    if max_park_time:
        hours = int(getattr(max_park_time, "hours", "0") or "0")
        minutes = int(getattr(max_park_time, "minutes", "0") or "0")
        return hours * 60 + minutes

    return None


def convert_max_park_time_to_hour_minutes(total_minutes):
    """
    Convert total minutes to hours and minutes.
    """
    max_park_time = {
        "hours": "",
        "minutes": ""
    }

    if total_minutes:
        hours = total_minutes // 60
        minutes = total_minutes % 60
        max_park_time["hours"] = str(hours).zfill(2)
        max_park_time["minutes"] = str(minutes).zfill(2)

    return max_park_time


def fetch_violation_amount(db,
                           parking_lot_id: int,
                           alert_id: int
                           ):
    credentials = db.query(base.User).filter(base.User.user_name == 'sg-connect-admin-api-client').first()
    if not credentials:
        raise ValueError("No credentials found for 'sg-connect-admin-api-client'.")

    attempts = 0
    max_attempts = settings.REQUEST_ATTEMPTS

    while attempts < max_attempts:
        # Check if the token exists; if not, attempt to fetch it
        if not credentials.token:
            form_data = {
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
            }
            token_response = requests.post(f"{settings.SPOT_GENIUS_API_BASE_URL}/api/oauth/token", data=form_data)
            if token_response.status_code == 200:
                # Extract and save the new token
                token = token_response.text.strip('"')
                credentials.token = token
                db.commit()
            else:
                raise RuntimeError("Failed to retrieve initial token. Check client credentials.")

        # Ensure token is available in headers
        headers = {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json",
        }

        response = requests.get(
            f"{settings.SPOT_GENIUS_API_BASE_URL}/api/external/v1/parking_lot/{parking_lot_id}/alert_type/{alert_id}/violation",
            headers=headers
        )

        if response.status_code == 401 and attempts < max_attempts - 1:
            # Refresh token if the current token is invalid
            form_data = {
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
            }
            token_response = requests.post(f"{settings.SPOT_GENIUS_API_BASE_URL}/api/oauth/token", data=form_data)
            if token_response.status_code == 200:
                # Extract and save the new token
                token = token_response.text.strip('"')
                credentials.token = token
                db.commit()
            else:
                raise RuntimeError("Failed to refresh token. Check client credentials.")
        elif response.status_code != 401:
            # Return the response if it's successful or if another error occurs
            return response.json()

        attempts += 1

    raise RuntimeError("Failed to fetch alert type after multiple attempts.")


def get_violation_id(violation_type: str):

    violation_id = {
        "payment.violation": 39,
        "overstay.violation": 2
    }

    return violation_id.get(violation_type, 0)


def calculate_time_differece(start_time):
    end_time = time.time()
    return end_time - start_time


def map_provider_action(provider):
    if provider.text_key == enum.ProviderTextKey.AdminFake.value:
        return 'Payment'

    provider_type = provider.provider_type.text_key.lower()
    for keyword in ('Reservation', 'Payment', 'Enforcement'):
        if keyword.lower() in provider_type:
            return keyword

    return ''
