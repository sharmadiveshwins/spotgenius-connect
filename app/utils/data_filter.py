from app.utils import enum
from datetime import datetime, timezone
import logging
import json
from app.utils.common import car_identification_log, DateTimeUtils
from app.models.task import Task
from Levenshtein import distance as levenshtein_distance
from urllib.parse import unquote

logger = logging.getLogger(__name__)


class DataFilter:

    @staticmethod
    def filter(provider_creds_text_key, task, data, lpr_matching_threshold_distance):
        closest_match_data = DataFilter.find_closest_match(data, task, lpr_matching_threshold_distance)
        if  (
                provider_creds_text_key == enum.Provider.PROVIDER_RESERVATION_TIBA.value
                and "closest_match_record" in closest_match_data and closest_match_data["closest_match_record"]
            ):
            closest_match_record = DataFilter.filter_tiba_data(
                                task, closest_match_data["closest_match_record"], closest_match_data["closest_match_plate"]
                            )
        else:
            closest_match_record = closest_match_data["closest_match_record"]

        return closest_match_record

    @staticmethod
    def filter_tiba_data(task, closest_match_record, closest_match_plate):
        # car_identification for dynamically showing logs for LPR or Spot based
        car_identification = car_identification_log(task)

        try:
            if DataFilter.tiba_other_cars_available(task, closest_match_record, closest_match_plate) and 'filtered_lpr_keys' in closest_match_record:
                logger.info(
                    f"Task: {task.id} / {car_identification} / Provider: TIBA / other LPR available in same lot"
                )
                return None   # Stop processing further records if peer car is already in parking lot

            closest_match_record['plate_number'] = closest_match_plate
            return closest_match_record

        except Exception as e:
            logger.warning(
                f"Task: {task.id} / {car_identification} - response - {json.dumps(closest_match_record)}")
            logger.critical(f"Tiba Filteration error: {str(e)}")


    def tiba_other_cars_available(task, data, closest_match_plate):
        secondary_lpr = [val for val in data['filtered_lpr_keys'] if
                         val != closest_match_plate]
        return Task.validate_secondary_lprs(plate_numbers=secondary_lpr, parking_lot_id=task.parking_lot_id) if len(
            secondary_lpr) > 0 else False


    @staticmethod
    def find_closest_match(records, task, max_distance=0):
        """
        Finds the closest match for the given target_plate from the list of records.

        Parameters:
            records (list of dicts): List of objects containing 'plate_number' or a list of plate numbers.
            target_plate (str): The plate number to match.
            max_distance (int): The maximum allowable Levenshtein distance for a match.
            
        Returns:
            dict or None: The best match object if found, otherwise None.
        """
        output = {
            "closest_match_record": None,
            "closest_match_plate": None # this needs for Tiba monthly pass checks
        }

        try:
            min_distance = float("inf")
            current_date = datetime.utcnow()

            for record in records:
                plate_numbers = record["plate_number"]  # Can be a string or list

                if 'paid_date' in record:
                    record['paid_date'] = DateTimeUtils.convert_to_iso_format(record['paid_date'])
                if 'expiry_date' in record:
                    record['expiry_date'] = DateTimeUtils.convert_to_iso_format(record['expiry_date'])

                # Normalize to a list (if it's a single string, convert it to a list)
                start = datetime.strptime(record.get("paid_date", "1990-01-01T12:00:00"), "%Y-%m-%dT%H:%M:%S")
                end = datetime.strptime(record.get("expiry_date", "1990-01-01T12:00:00"), "%Y-%m-%dT%H:%M:%S")

                if start <= current_date <= end and plate_numbers:
                    if isinstance(plate_numbers, str):
                        plate_numbers = [plate_numbers]

                    for plate in plate_numbers:
                        distance = levenshtein_distance(plate.upper(), task.plate_number.upper())
                        # If exact match, return immediately
                        if distance == 0:
                            logger.info(
                                f"Task: {task.id} / LPR: {task.plate_number} / Exact matched plate: {plate}")
                            record.update({"match_lpr": plate})

                            return {
                                "closest_match_record": record,
                                "closest_match_plate": task.plate_number
                            }

                        # Check if the distance is within the allowed threshold
                        if 0 < distance <= max_distance and distance < min_distance:
                            logger.info(
                                f"Task: {task.id} / LPR: {task.plate_number} / matched plate: {plate} / distance: {distance}")
                            record.update({"match_lpr": plate})

                            output["closest_match_record"] = record
                            output["closest_match_plate"] = plate # this needs for Tiba monthly pass checks
                            min_distance = distance

        except Exception as e:
            logger.error(f"Task: {task.id} / LPR: {task.plate_number} / Error in distance matching: {str(e)}")

        return output
