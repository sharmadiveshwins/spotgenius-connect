import logging
import requests
import json
import httpx
import asyncio
from pydantic.v1.schema import schema
from requests.auth import HTTPBasicAuth

from app.models import base
from app.models.provider import Provider
from app.models.provider_connect import ProviderConnect
from app.models.provider_creds import ProviderCreds
from app.utils import enum
from app.utils.request_handler import RequestHandler
from app.utils.response_handler import ResponseHandler
from app.config import settings
from app.utils.schema_mapping import SchemaMapping
from app.utils.security import decrypt_encrypted_value
from app.service import JCookie
from app.utils.common import car_identification_log, configure_alert_body, sanitize_logged_data, map_provider_action
import time
from app.utils.common import calculate_time_differece

logger = logging.getLogger(__name__)


class HttpWrapper:

    @staticmethod
    def check_request_method(db, task, sub_task, feature, provider_creds, connect_parkinglot, violation=None):
        if feature.request_method == enum.RequestMethod.POST.value:
            return HttpWrapper.post(db=db, task=task, sub_task=sub_task, feature=feature, provider_creds=provider_creds,
                                    connect_parkinglot=connect_parkinglot, violation=violation)
        if feature.request_method == enum.RequestMethod.GET.value:
            return HttpWrapper.get(db=db, task=task, sub_task=sub_task, feature=feature, provider_creds=provider_creds,
                                   connect_parkinglot=connect_parkinglot, violation=violation)

    @staticmethod
    def get(db, task, sub_task, feature, provider_creds, connect_parkinglot, violation=None):
        provider = Provider.get_by_id(db, provider_creds.provider_id)
        provider_connect = ProviderConnect.get_provider_connect(db, connect_id=connect_parkinglot.id,
                                                                provider_creds_id=provider_creds.id)
        url = provider.api_endpoint + feature.path
        models_dict = {
            'task': task,
            'sub_task': sub_task,
            'connect_parkinglot': connect_parkinglot,
            'provider_creds': provider_creds,
            'provider': provider,
            'provider_connect': provider_connect,
            'feature': feature,
        }
        url = RequestHandler.map_feature_url(url, models_dict)
        action = map_provider_action(provider)
        logger.warning(f"Task: {task.id} / LPR: {task.plate_number} - Checking {action} for {provider.name}")

        # add if condition for TIBA
        if provider.auth_type == enum.AuthType.BASIC.value and 'auth_info' in provider.meta_data.get('request'):
            auth = HTTPBasicAuth(provider.meta_data.get('request')['auth_info']['username'],
                                 decrypt_encrypted_value(provider.meta_data.get('request')['auth_info']['password']))
        else:
            auth = HTTPBasicAuth(provider_creds.client_id, decrypt_encrypted_value(provider_creds.client_secret))

        if provider.auth_type == enum.AuthType.OAUTH.value and provider_creds.access_token:
            headers = {
                'Authorization': f'Bearer {decrypt_encrypted_value(provider_creds.access_token)}'
            }
        elif provider.auth_type == enum.AuthType.BASIC.value and provider_creds.access_token:
            headers = {
                'Authorization': f'Basic {decrypt_encrypted_value(provider_creds.access_token)}'
            }

        else:
            headers = {}

        if feature.headers is not None:
            mapped_feature_headers = RequestHandler.update_feature_headers(provider_creds, feature.headers)
            headers.update(mapped_feature_headers)

        attempts = settings.CURRENT_ATTEMPTS
        logger.debug(f"Task: {task.id} / LPR: {task.plate_number} - Checking {action} for {provider.name}")

        request_start_time = time.time()
        logging.info(f"Task: {task.id} / LPR: {task.plate_number} - {provider.name} http request started.")

        while attempts <= settings.REQUEST_ATTEMPTS:

            try:

                if provider.auth_type == enum.AuthType.OAUTH.value:
                    response = requests.get(url, headers=headers, timeout=settings.REQUEST_TIMEOUT)
                else:
                    response = requests.get(url, auth=auth, headers=headers, timeout=settings.REQUEST_TIMEOUT)

                if response.status_code == 200:
                    logger.debug(f"Task: {task.id} / LPR: {task.plate_number} - "
                                 f"API request for {provider.name} Attempted {attempts}, "
                                 f"Status Received: {response.status_code}")

                    content_type = response.headers.get('content-type')
                    if 'xml' in content_type:
                        json_result = ResponseHandler.xml_to_json(response.text)
                        data = json.loads(json_result)
                        response = data
                    else:
                        response = response.json()
                    return response
                else:
                    logger.error(f"Task: {task.id} / LPR: {task.plate_number} - "
                                 f"API request for {provider.name} Attempted {attempts}, "
                                 f"Status Received: {response.status_code}")

                    if response.status_code == 401 and provider.auth_type == enum.AuthType.OAUTH.value:
                        auth_url = provider.api_endpoint + provider.oauth_path
                        form_data = provider.meta_data.get('oauth_info')
                        oauth_response = requests.post(auth_url, data=form_data)
                        auth_response = oauth_response.json()
                        access_token = auth_response.get('access_token')
                        headers.update({'Authorization': f'Bearer {access_token}'})

                    if response.status_code == 500:
                        from app.service import auth_service
                        access_token = auth_service.AuthService.generate_bearer_token(db, models_dict)
                        headers.update({'Authorization': f'Bearer {access_token}'})

                    elif response.status_code == 401 and provider.auth_type == enum.AuthType.JCOOKIE.value:
                        JCookie.auth(db, provider, provider_connect, provider_creds)
                        headers = RequestHandler.update_feature_headers(provider_creds, feature.headers)

                attempts += 1
            except Exception as e:
                logger.error(str(e))
                logger.critical(f"Task: {task.id} / LPR: {task.plate_number} - "
                                f"API request Failed for {provider.name} Attempted {attempts}")
                attempts += 1

        total_request_execution_time = calculate_time_differece(request_start_time)
        logging.info(f"Task: {task.id} / LPR: {task.plate_number} - {provider.name} http request completed in {total_request_execution_time:.2f} seconds.")

        return None


    @staticmethod
    def post(db, task, sub_task, feature, provider_creds, connect_parkinglot, violation=None):

        provider = Provider.get_by_id(db, provider_creds.provider_id)
        url = provider.api_endpoint + feature.path
        auth = None

        if violation is None:
            violation = base.Violation.get_violation_by_session_id(db, task.session_id,
                                                               violation_type=task.event_type)
        provider_connect = ProviderConnect.get_provider_connect(db, connect_id=connect_parkinglot.id,
                                                                provider_creds_id=provider_creds.id)
        session_by_id = base.Sessions.get_session_by_id(db, task.session_id)

        models_dict = {
            'task': task,
            'sub_task': sub_task,
            'connect_parkinglot': connect_parkinglot,
            'provider_creds': provider_creds,
            'violation': violation,
            'provider': provider,
            'provider_connect': provider_connect,
            'feature': feature,
        }

        # Replace placeholders in feature request schema with the specific data from specific table
        # e.g if we need a created_at date from xyz table will set value to {xyz.created_at}
        mapped_data = json.dumps(SchemaMapping.replace_json_placeholder_with_mapped_pointers(
            json.loads(feature.request_schema), models_dict))

        mapped_data = RequestHandler.replace_json_values(db, mapped_data, task, sub_task,
                                                         connect_parkinglot,
                                                         provider_creds, configure_alert_body(session_by_id, task))

        if feature.headers:
            headers = RequestHandler.update_feature_headers(provider_creds, feature.headers)
        else:
            headers = {"Content-Type": "application/json"}

        if feature.query_params:
            query_params = json.loads(feature.query_params)
            url = f"{url}?{'&'.join([f'{key}={value}' for key, value in query_params.items()])}"
        else:
            url = RequestHandler.map_feature_url(url, models_dict)

        if provider.auth_type == enum.AuthType.BASIC.value:
            auth = HTTPBasicAuth(provider_creds.client_id, decrypt_encrypted_value(provider_creds.client_secret))
        attempts = settings.CURRENT_ATTEMPTS

        # car_identification for dynamically showing logs for LPR or Spot based
        car_identification = car_identification_log(task)

        logger.debug(f"Task: {task.id} / {car_identification} - processing with provider {provider.name}")

        request_start_time = time.time()
        logging.info(f"Task: {task.id} / LPR: {task.plate_number} - {provider.name} http request started.")

        while attempts <= settings.REQUEST_ATTEMPTS:

            logger.info(f'Request to {provider.name} with data {sanitize_logged_data(mapped_data, ["image_base64s"])}')
            try:
                if provider.auth_type == "Token":
                    response = requests.post(url, data=json.dumps(mapped_data), headers=headers, timeout=settings.REQUEST_TIMEOUT)
                    logger.debug(f"Task: {task.id} / {car_identification} - "
                                 f"API request for {provider.name} Attempted {attempts}, "
                                 f"Status Received: {response.status_code}, "
                                 f"Response Received: {response.json()}")
                else:
                    response = requests.post(url, auth=auth, data=json.dumps(mapped_data), headers=headers, timeout=settings.REQUEST_TIMEOUT)

                if response.status_code == 200 and 'Error' not in response.json():
                    logger.debug(f"Task: {task.id} / {car_identification} - "
                                 f"API request for {provider.name} Attempted {attempts}, "
                                 f"Status Received: {response.status_code}, "
                                 f"Response Received: {response.json()}")
                    response = response.json()
                    return response
                else:
                    try:
                        json_response = response.json()
                    except json.JSONDecodeError:
                        json_response = {}
                    logger.error(f"Task: {task.id} / {car_identification} - "
                                 f"API request for {provider.name} Attempted {attempts}, "
                                 f"Status Received: {response.status_code}, "
                                 f"Response Received: {json_response}")

                    from app.service import auth_service

                    if ((response.status_code == 401 and provider.auth_type == enum.AuthType.LOGIN.value) or
                            (json_response.get('Error') in enum.DataTicket.AUTH_ERROR_MESSAGE.value and provider.auth_type == enum.AuthType.LOGIN.value)):
                        logger.error(f'Authentication failed for url: {url} with status code: {response.status_code}')
                        mapped_data = auth_service.AuthService.login(db, models_dict, mapped_data)

                    if (response.status_code == 401 or response.status_code == 500) and provider.auth_type == enum.AuthType.BASIC_BASE_64.value:
                        access_token = auth_service.AuthService.generate_basic_base_64(db, models_dict)
                        headers.update({'Authorization': access_token})

                attempts += 1
            except Exception as e:
                logger.critical(f"Task: {task.id} / {car_identification} - "
                                f"API request Failed for {provider.name} Attempted {attempts}")
                attempts += 1

        total_request_execution_time = calculate_time_differece(request_start_time)
        logging.info(f"Task: {task.id} / LPR: {task.plate_number} - {provider.name} http request completed in {total_request_execution_time:.2f} seconds.")

        return None
