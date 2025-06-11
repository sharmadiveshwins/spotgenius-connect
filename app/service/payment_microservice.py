import requests
import logging
from app.config import settings
from app.models.provider_connect import ProviderConnect
from sqlalchemy.orm import Session
from app.utils.common import calculate_time_differece
import time

from app.utils.security import decrypt_encrypted_value

logger = logging.getLogger(__name__)

class PaymentMicroService:
    max_retry_attempts = 2

    @staticmethod
    def check_payment(
        db: Session,
        provider_cred,
        parking_lot_id,
        grace_period,
        api_request_endpoint,
        lpr_matching_threshold_distance,
        feature,
        task,
        provider_text_key
    ):
        attempts = 0
        resposne = None

        request_start_time = time.time()
        logging.info(
            f"Task: {task.id} / LPR: {task.plate_number} / attempt {attempts} - {provider_text_key} payment-service request started."
        )

        while attempts < PaymentMicroService.max_retry_attempts:
            try:
                headers = {
                    "api_key": settings.PAYMENT_SERVICE_API_KEY,
                    "client_id": provider_cred.client_id,
                    "client_secret": decrypt_encrypted_value(provider_cred.client_secret)
                }

                provider_connect = ProviderConnect.get_by_cred_id(
                        db,
                        provider_creds_id=provider_cred.id
                    )

                params = {
                    "parking_lot_id": parking_lot_id,
                    "lpr": task.plate_number,
                    "spot_id": None,
                    "provider": provider_text_key,
                    "feature": feature,
                    "facility_id": provider_connect.facility_id,
                    "provider_api_key": provider_cred.api_key,
                    "grace_period": grace_period,
                    "lpr_text_match_threshold": lpr_matching_threshold_distance
                }

                meta_data = provider_cred.meta_data
                excluded_keys = ['client_id', 'client_secret', 'facility_id', 'requestDict']
                for key in excluded_keys:
                    meta_data.pop(key, None)
                params.update(meta_data)

                logger.debug(
                    f"Task: {task.id} / LPR: {task.plate_number} - "
                    f"API request for {provider_text_key} Attempted {attempts}, "
                    f"Request Params: {params}"
                )

                payment_info = requests.get(
                    url = f'{api_request_endpoint}/api/v1/connect/payments/sg-connect',
                    headers=headers,
                    params=params,
                    timeout=settings.REQUEST_TIMEOUT
                )

                logger.debug(
                    f"Task: {task.id} / LPR: {task.plate_number} - "
                    f"API request for {provider_text_key} Attempted {attempts}, "
                    f"Status Received: {payment_info.status_code}"
                )

                if payment_info and payment_info.status_code == 200:
                    payment_info_json = payment_info.json()

                    logger.debug(
                        f"Task: {task.id} / LPR: {task.plate_number} - "
                        f"API request for {provider_text_key} Attempted {attempts}, "
                        f"Respose Received: {payment_info_json}"
                    )

                    if 'data' in payment_info_json and payment_info_json['data']:
                        resposne = payment_info_json['data']
                        attempts = PaymentMicroService.max_retry_attempts

                attempts += 1

            except Exception as e:
                logger.error(e)
                logger.critical(
                    f"Task: {task.id} / LPR: {task.plate_number} - "
                    f"API request Failed for {provider_text_key} Attempted {attempts}"
                )
                attempts += 1

        total_request_execution_time = calculate_time_differece(request_start_time)
        logging.info(
            f"Task: {task.id} / LPR: {task.plate_number} - {provider_text_key} payment-service request completed in {total_request_execution_time:.2f} seconds."
        )

        return resposne
