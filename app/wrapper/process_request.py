import logging
from app.schema.response_integration_schema import ResponseIntegrationSchema
from app.wrapper.http_wrapper import HttpWrapper
from app.wrapper.soap_wrapper import SoapWrapper
from app.utils import enum

logger = logging.getLogger(__name__)


class ProcessRequest:

    @staticmethod
    def process(db, task, sub_task, feature, provider_creds, connect_parkinglot, violation=None) -> ResponseIntegrationSchema:
        if feature.api_type == enum.ApiType.REST.value:
            return HttpWrapper.check_request_method(db, task, sub_task, feature, provider_creds, connect_parkinglot, violation)
        if feature.api_type == enum.ApiType.SOAP.value:
            return SoapWrapper.check_request_method(db, task, feature, provider_creds, connect_parkinglot)
