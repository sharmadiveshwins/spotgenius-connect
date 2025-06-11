import logging
import xml.etree.ElementTree as ET
import json
from typing import Union, List, Dict, Optional

logger = logging.getLogger(__name__)


class ResponseHandler:

    @staticmethod
    def xml_to_dict(element):
        result = {}
        for child in element:
            tag = ResponseHandler.strip_namespace(child.tag)
            if child:
                child_data = ResponseHandler.xml_to_dict(child)
                if tag in result:
                    if type(result[tag]) is list:
                        result[tag].append(child_data)
                    else:
                        result[tag] = [result[tag], child_data]
                else:
                    result[tag] = child_data
            else:
                result[tag] = child.text
        return result

    @staticmethod
    def xml_to_json(response):
        root = ET.fromstring(response)
        data_dict = ResponseHandler.xml_to_dict(root)
        json_result = json.dumps(data_dict, indent=2, ensure_ascii=False)
        '''comment this because json_result have single quote values and after converting it was like "Joe"s Auto Park" '''
        # json_result = json_result.replace("'", '"')
        return json_result

    @staticmethod
    def strip_namespace(tag):
        # Function to strip XML namespace from the tag
        if '}' in tag:
            return tag.split('}')[1]
        return tag

    @staticmethod
    def replace_json_values(input_json: dict[str, str], mapping) -> dict[str, str]:
        result = {}

        def find_nested_value(data, target_key):
            for key, value in data.items():
                if isinstance(target_key, list):
                    return [find_nested_value(data, item) for item in target_key]

                if key == target_key:
                    return value
                elif isinstance(value, dict):
                    nested_result = find_nested_value(value, target_key)
                    if nested_result is not None:
                        return nested_result

                elif isinstance(value, list):
                    for item in value:
                        nested_result = find_nested_value(item, target_key)
                        if nested_result is not None:
                            return nested_result

            return None

        for key, value in mapping.items():
            nested_value = find_nested_value(input_json, value)
            if nested_value is not None:
                result[key] = nested_value
            else:
                pass
                # Handle the case where a key from the mapping is not present in the input JSON
        return result

    @staticmethod
    def replace_json_values_v2(input_json: Union[dict, list], mapping: dict) -> Optional[List[Dict]]:
        def find_first_list_or_dict(data):
            """Find the first occurrence of a non-empty list or dictionary in the JSON structure."""
            if isinstance(data, list):
                return data if data else None  # Return None for empty lists
            elif isinstance(data, dict):
                if any(k in str(mapping.values()) for k in data.keys()):
                    return [data]

                for key, value in data.items():
                    for value in data.values():
                        result = find_first_list_or_dict(value)
                        if result:
                            return result
                return None if not data else data  # Return None for empty dictionaries
            return None  # Return None for any unexpected type

        def find_nested_value(data, target_key):
            for key, value in data.items():
                if isinstance(target_key, list):
                    return [find_nested_value(data, item) for item in target_key]

                if key == target_key:
                    return value
                elif isinstance(value, dict):
                    nested_result = find_nested_value(value, target_key)
                    if nested_result is not None:
                        return nested_result

                elif isinstance(value, list):
                    for item in value:
                        nested_result = find_nested_value(item, target_key)
                        if nested_result is not None:
                            return nested_result

        # Find the first non-empty list or dictionary dynamically
        data_list = find_first_list_or_dict(input_json)

        # Return None if extracted data is None or an empty list/dictionary
        if not data_list:
            return None

        # Ensure data_list is iterable (wrap a dictionary in a list)
        if isinstance(data_list, dict):
            data_list = [data_list]

        result = []
        for item in data_list:
            transformed_item = {}
            
            for new_key, old_key in mapping.items():
                value = find_nested_value(item, old_key)
                if isinstance(old_key, list):
                    # Merge multiple fields into a single list under new_key
                    transformed_item[new_key] = value if value else None
                else:
                    transformed_item[new_key] = value

            # Ensure we only append non-empty transformed dictionaries
            if any(transformed_item.values()):
                result.append(transformed_item)

        return result if result else None  # Return None if the result list is empty






