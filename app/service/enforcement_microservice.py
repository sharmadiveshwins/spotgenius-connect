import logging
import time

import requests
from app.config import settings
from app.schema.citation_schema import EnforcementServiceSchema
from app.service.auth_service import decrypt_encrypted_value
from app.models.provider_connect import ProviderConnect
from app.utils.common import calculate_time_differece

logger = logging.getLogger(__name__)


class EnforcementMicroService:

    max_retry_attempts = 2

    @staticmethod
    def create_citation(
            task,
            provider_text_key,
            provider_cred,
            api_request_endpoint,
            schema: EnforcementServiceSchema
    ):
        attempts = 0
        response = None

        request_start_time = time.time()
        logging.info(
            f"Task: {task.id} / LPR: {task.plate_number} / attempt {attempts} - {provider_text_key} enforcement-service request started."
        )

        while attempts < EnforcementMicroService.max_retry_attempts:

            try:

                headers = {
                    "api_key": settings.ENFORCEMENT_SERVICE_API_KEY,
                    "client_id": provider_cred.client_id,
                    "client_secret": decrypt_encrypted_value(provider_cred.client_secret)
                }

                logger.debug(
                    f"Task: {task.id} / LPR: {task.plate_number} - "
                    f"API request for {provider_text_key} Attempted {attempts}, "
                    f"Request Body: {schema}"
                )

                enforcement_response = requests.post(
                    url=f'{api_request_endpoint}/api/v1/connect/violation/sg-connect',
                    headers=headers,
                    data=schema.json(),
                    timeout=settings.REQUEST_TIMEOUT
                )

                logger.debug(
                    f"Task: {task.id} / LPR: {task.plate_number} - "
                    f"API request for {provider_text_key} Attempted {attempts}, "
                    f"Status Received: {enforcement_response.status_code}"
                )

                if enforcement_response and enforcement_response.status_code == 201:

                    enforcement_body_response = enforcement_response.json()

                    logger.debug(
                        f"Task: {task.id} / LPR: {task.plate_number} - "
                        f"API request for {provider_text_key} Attempted {attempts}, "
                        f"Response Received: {enforcement_response}"
                    )

                    if 'data' in enforcement_body_response and enforcement_body_response['data']:
                        response = enforcement_body_response
                        attempts = EnforcementMicroService.max_retry_attempts

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

        return response


