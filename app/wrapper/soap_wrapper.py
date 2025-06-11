import requests
import json

from app.models.provider import Provider
from app.schema.response_integration_schema import ResponseIntegrationSchema
from app.utils.response_handler import ResponseHandler
from app.utils.request_handler import RequestHandler
from app.utils import enum
from app.config import settings
import logging
from app.utils.common import calculate_time_differece
import time

from app.utils.security import decrypt_encrypted_value

logger = logging.getLogger(__name__)


class SoapWrapper:

    @staticmethod
    def check_request_method(db, task, feature, provider_creds, connect_parkinglot) -> ResponseIntegrationSchema:
        if feature.request_method == enum.RequestMethod.POST.value:
            return SoapWrapper.post(db, task, feature, provider_creds, connect_parkinglot)
        if feature.request_method == enum.RequestMethod.GET.value:
            return SoapWrapper.get(db, task, feature, provider_creds, connect_parkinglot)

    @staticmethod
    def get(db, task, feature, provider_creds, connect_parkinglot):
        provider = Provider.get_by_id(db, provider_creds.provider_id)
        url = provider.api_endpoint + feature.path
        attempts = settings.CURRENT_ATTEMPTS

        url = RequestHandler.map_path_params(url, task, connect_parkinglot)

        username = provider_creds.client_id
        password = decrypt_encrypted_value(provider_creds.client_secret)

        logger.debug(f"Task: {task.id} / LPR: {task.plate_number} - Checking Payment for {provider.name}")

        request_start_time = time.time()
        logging.info(f"Task: {task.id} / LPR: {task.plate_number} - {provider.name} soap request started.")

        while attempts <= settings.REQUEST_ATTEMPTS:
            try:
                requests_post = requests.get(url, auth=(username, password), timeout=settings.REQUEST_TIMEOUT)
                if requests_post.status_code == 200:
                    logger.debug(
                        f"Task: {task.id} / LPR: {task.plate_number} - API request for {provider.name} Attempted {attempts}, Status Received: {requests_post.status_code}")
                    json_result = ResponseHandler.xml_to_json(requests_post.text)
                    data = json.loads(json_result)
                    return data
                else:
                    logger.error(
                        f"Task: {task.id} / LPR: {task.plate_number} - API request for {provider.name} Attempted {attempts}, Status Received: {requests_post.status_code}")
                attempts += 1
            except Exception as e:
                logger.critical(
                    f"Task: {task.id} / LPR: {task.plate_number} - API request Failed for {provider.name} Attempted {attempts}")
                attempts += 1

        total_request_execution_time = calculate_time_differece(request_start_time)
        logging.info(f"Task: {task.id} / LPR: {task.plate_number} - {provider.name} soap request completed in {total_request_execution_time:.2f} seconds.")
        
        return None

    @staticmethod
    def post(db, task, feature, provider_creds, connect_parkinglot):
        provider = Provider.get_by_id(db, provider_creds.provider_id)
        request_data = feature.request_schema.replace('{{', '{').replace('}}', '}')
        mapped_data = RequestHandler.map_value(request_data, provider_creds.meta_data, task)
        headers_dict = json.loads(feature.headers)
        url = provider.api_endpoint + feature.path
        attempts = settings.CURRENT_ATTEMPTS

        logger.debug(f"Task: {task.id} / LPR: {task.plate_number} - Checking Payment for {provider.name}")

        request_start_time = time.time()
        logging.info(f"Task: {task.id} / LPR: {task.plate_number} - {provider.name} soap request started.")

        while attempts <= settings.REQUEST_ATTEMPTS:
            try:
                requests_post = requests.post(url, data=mapped_data, headers=headers_dict, timeout=settings.REQUEST_TIMEOUT)
                if requests_post.status_code == 200:
                    logger.debug(
                        f"Task: {task.id} / LPR: {task.plate_number} - API request for {provider.name} Attempted {attempts}, Status Received: {requests_post.status_code}")
                    json_result = ResponseHandler.xml_to_json(requests_post.text)
                    data = json.loads(json_result)
                    return data
                else:
                    logger.error(
                        f"Task: {task.id} / LPR: {task.plate_number} - API request for {provider.name} Attempted {attempts}, Status Received: {requests_post.status_code}")
                attempts += 1
            except Exception as e:
                logger.critical(
                    f"Task: {task.id} / LPR: {task.plate_number} - API request Failed for {provider.name} Attempted {attempts}")
                attempts += 1
        
        total_request_execution_time = calculate_time_differece(request_start_time)
        logging.info(f"Task: {task.id} / LPR: {task.plate_number} - {provider.name} soap request completed in {total_request_execution_time:.2f} seconds.")

        return None
