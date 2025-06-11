from app.utils import enum
from datetime import datetime
import logging
import json
from app.utils.common import car_identification_log
from app.models.task import Task
from urllib.parse import unquote

logger = logging.getLogger(__name__)


class DataFilter:

    @staticmethod
    def filter(provider_creds_text_key, task, data, feature_response_schema):
        if provider_creds_text_key == enum.Provider.PROVIDER_RESERVATION_TIBA.value:
            data = DataFilter.filter_tiba_data(task, data, feature_response_schema)
        elif provider_creds_text_key == enum.Provider.PROVIDER_PAYMENT_OOBEO.value:
            data = DataFilter.filter_oobeo_data(task, data)

        return data

    @staticmethod
    def filter_tiba_data(task, data, feature_response_schema):
        # car_identification for dynamically showing logs for LPR or Spot based
        car_identification = car_identification_log(task)

        try:
            output = None
            current_date = datetime.now()

            def get_records(data):
                for record in data.get('ListItems'):
                    yield record  # Yield each record one at a time

            # Use the generator to process records one at a time
            for record in get_records(data):

                valid_from = datetime.strptime(record.get("ValidFrom") or record.get("ValidFromStr"), "%d-%m-%Y" "T" "%H:%M:%S")
                valid_to = datetime.strptime(record.get("ValidTo") or record.get("ValidToStr"), "%d-%m-%Y" "T" "%H:%M:%S")

                if valid_from <= current_date <= valid_to and any(record.get(key).lower() == task.plate_number.lower() for key in feature_response_schema['filtered_lpr_keys']):
                    if DataFilter.tiba_other_cars_available(task, record, feature_response_schema):
                        break  # Stop processing further records if peer car is already in parking lot

                    output = record
                    output[feature_response_schema['plate_number']] = task.plate_number
                    break  # Stop processing further records if a match is found

            return output

        except Exception as e:
            logger.warning(
                f"Task: {task.id} / {car_identification} - response - {json.dumps(data)}")
            logger.critical(f"Tiba Filteration error: {str(e)}")


    def tiba_other_cars_available(task, data, feature_response_schema):
        secondary_lpr = [data.get(key) for key in feature_response_schema['filtered_lpr_keys'] if
                         data.get(key) != task.plate_number and data.get(key)]
        return Task.validate_secondary_lprs(plate_numbers=secondary_lpr, parking_lot_id=task.parking_lot_id) if len(
            secondary_lpr) > 0 else False


    def filter_oobeo_data(task, data):
        # car_identification for dynamically showing logs for LPR or Spot based
        car_identification = car_identification_log(task)

        try:
            output = None
            current_date = datetime.now()

            def get_records(data):
                for record in data.get('vehicles'):
                    yield record  # Yield each record one at a time

            # Use the generator to process records one at a time
            for record in get_records(data):
                start = datetime.strptime(record.get("start"), "%Y-%m-%dT%H:%M:%S.%fZ")
                end = datetime.strptime(record.get("end"), "%Y-%m-%dT%H:%M:%S.%fZ")

                if start <= current_date <= end and task.plate_number == record.get("license_plate_number"):
                    output = record
                    break  # Stop processing further records if a match is found

            return output

        except Exception as e:
            logger.warning(
                f"Task: {task.id} / {car_identification} - response - {json.dumps(data)}")
            logger.critical(f"Oobeo Filteration error: {str(e)}")
