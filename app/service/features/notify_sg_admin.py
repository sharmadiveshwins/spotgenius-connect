import json
import logging

from app.models import base
from app.models.feature_url_path import FeatureUrlPath
from app.models.provider_creds import ProviderCreds
from app.models.sessions import Sessions
from app.schema.response_integration_schema import ResponseIntegrationSchema
from app.service import session_manager
from app.service.payment_service import PaymentService
from app.wrapper.process_request import ProcessRequest
from app.utils.response_handler import ResponseHandler
import traceback
from app.utils.violation_rule import ViolationRule
from app.utils import enum

logger = logging.getLogger(__name__)


class NotifySgAdmin:

    @staticmethod
    def send_alerts(db: Sessions, task, sub_tasks):
        try:
            # check if spot is already free or car get exited
            exit_status = False
            session = base.Sessions.get_session_by_id(db, session_id=task.session_id)

            if task.plate_number:
                exit_status = ViolationRule.lpr_exit_status(db, task.parking_lot_id, session.lpr_record_id)
            elif task.parking_spot_name:
                exit_status = ViolationRule.spot_free_status(db, task.parking_lot_id, task.parking_spot_name)

            if exit_status:
                NotifySgAdmin.close_associated_enforcement_task(db, task, "exit_status : True")
                return

            connect_parkinglot = base.ConnectParkinglot.get_connect_parking_lot_id(db, task.parking_lot_id)
            for sub_task in sub_tasks:
                feature_by_id = FeatureUrlPath.get_feature_url_path_by_id(db, sub_task.feature_url_path)
                provider_creds_by_id = ProviderCreds.get_by_id(db, sub_task.provider_creds_id)
                data = ProcessRequest.process(db=db,
                                            task=task,
                                            sub_task=sub_task,
                                            feature=feature_by_id,
                                            provider_creds=provider_creds_by_id,
                                            connect_parkinglot=connect_parkinglot
                                            )
                json_response_schema = json.loads(feature_by_id.response_schema)
                if data is not None:
                    results = ResponseHandler.replace_json_values(data, json_response_schema)

                    if results is not None:
                        response_schema = ResponseIntegrationSchema(
                            response_id=[results.get("response_id")],
                            image=results.get("vehicle_image")
                        )

                        task = base.Task.update_task(db, task, response_schema.response_id)
                        base.Task.append_lr_image_to_sg_event_response(db, task.session_id, "lr_image", response_schema.image)

                        logger.info(f'Task: {task.id} / LPR: {task.plate_number} - Violation Alert is generate with id : {response_schema.response_id}')

                        action_type = enum.EventsForSessionLog.Payment_alert.value
                        if task.event_type == enum.EventTypes.OVERSTAY_VIOLATION.value:
                            action_type = enum.EventsForSessionLog.Overstay_alert.value
                        session_manager.SessionManager.create_session_logs(db,
                                                                        session_id=task.session_id,
                                                                        action_type=action_type,
                                                                        description=action_type
                                                                        )
                    else:
                        NotifySgAdmin.close_associated_enforcement_task(db, task, "results : None")

                else:
                    NotifySgAdmin.close_associated_enforcement_task(db, task, "data : None")

        except Exception as e:
            # Log the full error with traceback details
            error_message = f"An error occurred: {e}"
            traceback_details = traceback.format_exc()
            logger.error(error_message)
            logger.error(f"Traceback details:\n{traceback_details}")


    @staticmethod
    def close_associated_enforcement_task(db, task, closed_from):
        enforcement_task = base.Task.close_enforcement_task_sub_task(
            db=db, session_id=task.session_id, event_type=task.event_type, feature_text_type=enum.Feature.ENFORCEMENT_CITATION.value
        )

        if enforcement_task:
            logger.info(
                f'Task: {task.id} / LPR: {task.plate_number} - closed enforcement task with id : {enforcement_task.id} / {closed_from}'
            )