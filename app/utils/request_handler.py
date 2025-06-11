import logging
import re
import json
import aiohttp
from datetime import datetime, timedelta, timezone
from app.schema.common_schema import CommonSchema
from app.models import base
from app.utils.schema_mapping import SchemaMapping
from app.utils import common, enum

logger = logging.getLogger(__name__)


class RequestHandler:
    """
    {{plateNumber}} -> task.plate_number
    {{spotId}} -> task.parking_spot_id
    {{parkingLot}} -> task.parking_lot_id
    {{facilityId}} -> provider_connect.facility_id
    """

    @staticmethod
    def map_value(request_data, json_to_map, task):

        request_dict = json_to_map.get("requestDict")
        if task.plate_number:
            plate_number = task.plate_number
            request_dict.update(CommonSchema(plateNumber=plate_number,
                                             parking_lot_id=task.parking_lot_id))
        else:
            request_dict.update(CommonSchema(parking_spot_id=task.parking_spot_id,
                                             parking_lot_id=task.parking_lot_id))

        if not request_dict:
            return request_data

        json_keys = request_dict.keys()
        pattern = re.compile(r'\{(' + '|'.join(map(re.escape, json_keys)) + r')\}')

        def replace(match):
            key = match.group(1)
            return str(request_dict.get(key, ''))

        updated_request_data = pattern.sub(replace, request_data)
        return updated_request_data

    @staticmethod
    def replace_json_values(db, schema, task, sub_task, connect_parkinglot, provider_creds, alert_body):

        try:
            schema_dict = json.loads(schema)
            violation = base.Violation.get_violation_by_session_id(db, task.session_id, violation_type=enum.EventTypes.PAYMENT_VIOLATION.value)
        except Exception as e:
            logger.critical(f"Exception: {str(e)}")
            return schema

        if connect_parkinglot and provider_creds:
            provider_connect = base.ProviderConnect.get_provider_connect(db, connect_parkinglot.id,
                                                                         sub_task.provider_creds_id)

        def replace_values(data):
            if isinstance(data, dict):
                for key, value in data.items():
                    if value == "current_timestamp":
                        data[key] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                    elif value == 'location_id':
                        if provider_connect:
                            data[key] = provider_connect.facility_id

                    elif isinstance(value, str):
                        if isinstance(task, dict) and value in task:
                            data[key] = task[value]
                        elif hasattr(task, '__dict__') and hasattr(task, value):
                            data[key] = getattr(task, value)
                        elif hasattr(sub_task, '__dict__') and value in vars(sub_task):
                            data[key] = vars(sub_task)[value]
                        elif hasattr(violation, '__dict__') and value in vars(violation):
                            data[key] = vars(violation)[value]
                        elif hasattr(provider_creds, '__dict__') and value in vars(provider_creds):
                            data[key] = vars(provider_creds)[value]
                        elif hasattr(connect_parkinglot, '__dict__') and value in vars(connect_parkinglot):
                            data[key] = vars(connect_parkinglot)[value]
                        elif isinstance(alert_body, dict) and value in alert_body:
                            data[key] = alert_body[value]
                    elif isinstance(value, (dict, list)):
                        replace_values(value)
            elif isinstance(data, list):
                for item in data:
                    replace_values(item)

        replace_values(schema_dict)
        return schema_dict

    @staticmethod
    async def make_post_request(url, data):
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                return await response.text()

    @staticmethod
    def map_path_params(url, task, connect_parkinglot):
        url = url.replace('{lpr}', str(task.plate_number))
        url = url.replace('{gracePeriod}', str(connect_parkinglot.grace_period))
        return url

    @staticmethod
    def map_key_values(original_dict, task):
        return RequestHandler.get_nested_values(task, original_dict)

    @staticmethod
    def get_nested_values(obj, key_paths, separator="."):
        """
        Retrieve multiple nested values from an object using key paths.

        :param obj: The object (e.g., SQLAlchemy model instance) to retrieve the values from.
        :param key_paths: A dictionary of key path strings (e.g., ["attribute1.attribute2", "attribute3"]).
        :param separator: The separator used in the key paths (default is ".").
        :return: A dictionary with key paths as keys and the retrieved values as values.
        """
        for object, key_path in key_paths.items():
            if isinstance(key_path, str):
                keys = key_path.split(separator)
                value = obj

                for key in keys:
                    if isinstance(value, dict):
                        value = value.get(key)
                    else:
                        value = getattr(value, key, None)
                    if value is None:
                        break

                key_paths[object] = value

        return key_paths

    @staticmethod
    def map_request_params(models):

        query_params = SchemaMapping.replace_json_placeholder_with_mapped_pointers(json.loads(models['feature'].query_params), models)

        params = {}
        for data in query_params:
            formatted = common.format_params(data)
            params.update({
                data['key']: formatted
            })

        return params
    
    @staticmethod
    def make_request_data(request_schema):
        header, body, url, method = {}, {}, '', 'POST'

        if 'request' in request_schema:
            if 'method' in request_schema:
                method = request_schema['request']['method']

            if 'headers' in request_schema['request']:
                header.update(request_schema['request']['headers'])
            
            if 'body' in request_schema['request']:
                for body_data in request_schema['request']['body']:
                    body_data['value'] = SchemaMapping.original_value(body_data['key'], body_data['value'])

                    body.update({
                        body_data['key']: body_data['value']
                    })

            if 'url' in request_schema['request']:
                if 'host' in request_schema['request']['url']:
                    url += request_schema['request']['url']['host']

                if 'tenant_id' in request_schema['request']['url']:
                    url += f"/{request_schema['request']['url']['tenant_id']}"

                if 'path' in request_schema['request']['url']:
                    url += request_schema['request']['url']['path']

        return {
            'method': method,
            'url': url,
            'body': body,
            'headers': header
        }
    
    @staticmethod
    def map_feature_url(url, models_dict):

        if (models_dict['provider'].meta_data and 'request' in models_dict['provider'].meta_data
                and 'url' in models_dict['provider'].meta_data['request']):

            request_output_schema = SchemaMapping.replace_json_placeholder_with_mapped_pointers(models_dict['provider'].meta_data['request']['url'], models_dict)
            if 'tenant_id' in request_output_schema:
                url = models_dict['provider'].api_endpoint + f"/{request_output_schema['tenant_id']}" + models_dict['feature'].path

        if models_dict['feature'].query_params:
            query_params = RequestHandler.map_request_params(models_dict)

            url = f"{url}?{'&'.join([f'{key}={value}' for key, value in query_params.items()])}"

        url = RequestHandler.replace_path_params(url, models_dict)

        return url
    
    @staticmethod
    def update_feature_headers(provider_creds, feature_headers):
        mapped_header_data = {
            "provider_creds": provider_creds
        }
        return SchemaMapping.replace_json_placeholder_with_mapped_pointers(json.loads(feature_headers), mapped_header_data)

    @staticmethod
    def replace_path_params(val, replace_from):
        """Helper function to resolve a placeholder string with actual data."""
        placeholders = re.findall(r'\{([^{}]*)}', val)
        for placeholder in placeholders:
            if isinstance(placeholder, str):
                model = common.split_first_dot(placeholder)
                if isinstance(model, tuple) and model[0] in replace_from:
                    # Check for simple attributes or nested attributes with key paths
                    if hasattr(replace_from[model[0]], model[1]):
                        replaced_data = SchemaMapping.original_value(model[1],
                                                                     getattr(replace_from[model[0]],
                                                                             model[1]))

                        val = val.replace(f"{{{placeholder}}}", str(replaced_data)) if replaced_data else replaced_data
        return val

