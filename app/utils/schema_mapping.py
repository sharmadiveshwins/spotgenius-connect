import json
import logging
from typing import Dict, Any, List

from fastapi import HTTPException

from app.schema.citation_schema import CreateCitationSchema
from app.schema.register_lot import RegisterLotSchema
from app.schema.provider_auth_schema import EnforcementProvider
from app.utils import common
from app.utils.image_utils import ImageUtils
from app.utils.security import decrypt_encrypted_value
from app.utils import enum
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class SchemaMapping:

    @staticmethod
    def map_values_to_request_schema(task, request_schema):
        try:
            request_schema_dict = json.loads(request_schema)
        except Exception as e:
            logger.critical(f"Exception {str(e)}")
            raise HTTPException(status_code=500, detail="Error decoding request schema JSON: {}".format(str(e)))

        attribute_mapping = {
            "parking_lot_id": "parking_lot_id",
            "parking_spot_id": "parking_spot_id"
        }

        mapped_data = {}
        for key, attribute in attribute_mapping.items():
            if key in request_schema_dict:
                mapped_data[key] = getattr(task, attribute, None)

        return mapped_data

    @staticmethod
    def map_values_to_response_schema():
        pass

    @staticmethod
    def map_values_to_park_pliant_schema(source_item: RegisterLotSchema) -> EnforcementProvider.RegisterLotWithProvider:
        return EnforcementProvider.RegisterLotWithProvider(
            code=str(source_item.parkingLotId),
            displayName=source_item.displayName,
            address=source_item.address,
            city=source_item.city,
            state=source_item.state,
            zip=source_item.zip,
            ianaTimezone=source_item.ianaTimezone,
            latitude=0,
            longitude=0,
            signImageUrls=source_item.signImageUrls
        )

    @staticmethod
    def map_value_to_citation_schema(source_item: CreateCitationSchema, target_schema) -> List[Dict[str, Any]]:
        mapped_data = [{key: getattr(source_item, key) for key in target_schema.keys() if hasattr(source_item, key)}]
        return mapped_data

    @staticmethod
    def get_key_path_mapping_values(obj, key_path, separator='.'):
        if isinstance(key_path, str):
            keys = key_path.split(separator)
            value = obj

            for key in keys:
                if isinstance(value, dict):
                    value = SchemaMapping.original_value(key, value.get(key))
                else:
                    value = SchemaMapping.original_value(key, getattr(value, key, None))
                if value is None:
                    break

            return value

    @staticmethod
    def original_value(key, value):
        try:
            if key in enum.Encryption.COLUMNS.value:
                value = decrypt_encrypted_value(value)
            elif value is None:
                value = ''
        except Exception as e:
            logger.debug(e)

        return value

    # TODO
    # need enhancement in below function
    @staticmethod
    def replace_json_placeholder_with_mapped_pointers(json_obj, replace_value_dict):
        import re

        def resolve_placeholder(val, replace_from):
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
                            if isinstance(replaced_data, dict):
                                request_dict = replaced_data.get('requestDict',
                                                                 {})

                                if isinstance(request_dict, dict) and json_obj.get("key", "") in request_dict:
                                    placeholder_key = json_obj.get("key", "")
                                    val = request_dict[placeholder_key]
                                    json_obj[key] = val

                            # json_obj[key] = val.replace(f"{{{placeholder}}}",
                            #                             str(replaced_data)) if replaced_data else replaced_data
                            # val = val.replace(f"{{{placeholder}}}", str(replaced_data)) if replaced_data else replaced_data
                            val = val.replace(f"{{{placeholder}}}",
                                                        str(replaced_data))
                            json_obj[key] = val if val else replaced_data

                        elif isinstance(model, tuple) and model[0] in replace_from and isinstance(
                                        replace_from[model[0]], object) and '.' in model[1]:
                            replaced_data = SchemaMapping.get_key_path_mapping_values(replace_from[model[0]],
                                                                                              model[1])
                            # json_obj[key] = val.replace(f"{{{placeholder}}}", str(replaced_data)) if replaced_data else replaced_data
                            # val = json_obj[key]
                            val = val.replace(f"{{{placeholder}}}",
                                                        str(replaced_data))
                            json_obj[key] = val if val else replaced_data

            return val

        if isinstance(json_obj, dict):
            for key, value in json_obj.items():
                if isinstance(value, str):

                    if value == 'current_utc':
                        json_obj[key] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

                    resolve_placeholder(value, replace_value_dict)

                elif isinstance(value, dict) and 'type' in value and value['type'] == 'base64':
                    # Handle base64 type transformations
                    url = resolve_placeholder(value['value'], replace_value_dict)
                    if url is not None and url != '' and url != 'None':
                        json_obj[key] = ImageUtils.image_url_to_base64(url)
                    else:
                        json_obj[key] = ""

                elif isinstance(value, (dict, list)):
                    json_obj[key] = SchemaMapping.replace_json_placeholder_with_mapped_pointers(value,
                                                                                                replace_value_dict)
        elif isinstance(json_obj, list):
            for item in json_obj:
                SchemaMapping.replace_json_placeholder_with_mapped_pointers(item, replace_value_dict)

        return json_obj