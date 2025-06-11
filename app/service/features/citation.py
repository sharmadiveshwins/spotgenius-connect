import logging
import json
from sqlalchemy.orm import Session

from app.models.feature_url_path import FeatureUrlPath
from app.models.provider_creds import ProviderCreds
from app.models.sub_task import SubTask
from app.schema.citation_schema import EnforcementServiceSchema
from app.service import session_manager
from app.service.enforcement_microservice import EnforcementMicroService
from app.utils import enum
from app.utils.response_handler import ResponseHandler
from app.wrapper.process_request import ProcessRequest
from app.models import base
from app.utils.common import car_identification_log
import traceback
from app.utils.violation_rule import ViolationRule

logger = logging.getLogger(__name__)


class Citation:

    @staticmethod
    def create_citation(db: Session, task, sub_tasks):
        # check task is closed after passed into Huey worker. This condition was added because we are closing enforcement task when related SG Admin alert not created
        task_status = base.Task.get_column_value_by_id(db, task.id, 'status')
        if task_status == enum.TaskStatus.CLOSED.value:
            logger.info(
                f'Task: {task.id} / LPR: {task.plate_number} - task already closed'
            )
            return

        # check if spot is already free or car get exited
        exit_status = False
        session = base.Sessions.get_session_by_id(db, session_id=task.session_id)
        if task.parking_spot_name:
            exit_status = ViolationRule.spot_free_status(db, task.parking_lot_id, task.parking_spot_name)
        elif task.plate_number:
            exit_status = ViolationRule.lpr_exit_status(db, task.parking_lot_id, session.lpr_record_id)

        if exit_status:
            return None

        connect_parkinglot = base.ConnectParkinglot.get_connect_parking_lot_id(db, task.parking_lot_id)
        for sub_task in sub_tasks:
            feature_by_id = FeatureUrlPath.get_feature_url_path_by_id(db, sub_task.feature_url_path)
            provider_creds_by_id = ProviderCreds.get_by_id(db, sub_task.provider_creds_id)
            provider_obj = base.Provider.get_provider_by_id(db, provider_creds_by_id.provider_id)
            violation = base.Violation.get_violation_by_task_and_session_id(db, task.id, session.id)

            # call enforcement service if provider_obj.provider_api_request_type is not sgconnect
            if provider_obj.provider_api_request_type != enum.ProviderApiRequestType.Connect.value:

                provider_connect = base.ProviderConnect.get_by_cred_id(
                    db,
                    provider_creds_id=provider_creds_by_id.id
                )

                try:
                    mapped_request = Citation.create_enforcement_service_request(
                        provider=provider_obj,
                        provider_creds=provider_creds_by_id,
                        violation=violation,
                        facility_id=provider_connect.facility_id,
                        task=task
                    )

                    data = EnforcementMicroService.create_citation(
                        task=task,
                        provider_text_key=provider_obj.text_key,
                        provider_cred=provider_creds_by_id,
                        api_request_endpoint=provider_obj.api_request_endpoint,
                        schema=mapped_request
                    )

                except Exception as e:
                    logger.error(
                        f'Task: {task.id} / LPR: {task.plate_number} - for provider {provider_obj.name} / error: {str(e)}'
                    )

            else:

                data = ProcessRequest.process(db=db,
                                            task=task,
                                            sub_task=sub_task,
                                            feature=feature_by_id,
                                            provider_creds=provider_creds_by_id,
                                            connect_parkinglot=connect_parkinglot
                                            )

            provider_name = base.Provider.get_provider_by_id(db, provider_creds_by_id.provider_id).name
            logger.info(f'Received response {data} from provider {provider_name}')
            json_response_schema = json.loads(feature_by_id.response_schema)
            if data is not None:
                results = ResponseHandler.replace_json_values(data, json_response_schema)
                if results['status']:
                    # attribute_to_update = {"citation_id": results.get('response_id')}
                    # violation = base.Violation.update_by_session_and_task(db, task.session_id, task.id,
                    #                                                      attribute_to_update)
                    violation.citation_id = results.get('response_id')

                    logger.info(f'Response id mapped with Violation for session {task.session_id}')

                    # car_identification for dynamically showing logs for LPR or Spot based
                    car_identification = car_identification_log(task)

                    logger.info(
                        f"Task: {task.id} / {car_identification} - Citation Created")
                    provider_creds_by_id = base.ProviderCreds.get_by_id(db, sub_task.provider_creds_id)
                    provider = base.Provider.get_by_id(db, provider_creds_by_id.provider_id)
                    session_manager.SessionManager.create_session_logs(db=db,
                                                                       session_id=task.session_id,
                                                                       action_type=f"{enum.EventsForSessionLog.VIOLATION_SENT.value}: {violation.name}",
                                                                       description=f"Reference #: {results.get('response_id')},"
                                                                                   f"Violation name: {violation.name}, "
                                                                                   f"Violation penalty: ${violation.meta_data.get('amount', 0)}"
                                                                                   f"{', Code: ' + results['viocode'] if results.get('viocode') else ''}",
                                                                       provider=provider.id if provider is not None else None,
                                                                       )
                    return data

            SubTask.close_sub_task(db, sub_task.id)


    @staticmethod
    def create_enforcement_service_request(provider, provider_creds, violation, facility_id, task):

        mapped_schema = EnforcementServiceSchema(
            lpr=task.plate_number,
            state=task.state if task.state else None,
            violation_time=violation.timestamp,
            entry_time=task.sg_event_response.get('timestamp'),
            amount=violation.meta_data.get('amount', 0),
            violation_title=violation.name,
            facility_id="",
            feature="lpr",
            provider_key=provider.text_key,
            parking_lot_id=task.parking_lot_id,
            citation_id=str(violation.id),
            spot_name=task.parking_spot_name if task.parking_spot_name else None,
            make=task.sg_event_response.get('make'),
            color=task.sg_event_response.get('color'),
            body=task.sg_event_response.get('model')

        )

        return mapped_schema

