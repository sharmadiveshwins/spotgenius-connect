import logging
from sqlalchemy.orm import Session
import requests
from app.utils.schema_mapping import SchemaMapping
from app.models.task import Task


logger = logging.getLogger(__name__)


def get_payment_status(event, access_token, feature_url, db: Session):

    feature_url_obj = Task.get_feature_url(db, event.id)
    headers = {
        "content-type": "application/json",
        "Authorization": "Bearer {}".format(access_token),
    }

    request_schema = feature_url_obj.request_schema
    mapped_schema = SchemaMapping.map_values_to_request_schema(event, request_schema)
    response = requests.post(feature_url, json=mapped_schema, headers=headers)
    return response
