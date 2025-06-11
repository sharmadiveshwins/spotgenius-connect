import json
import logging
from datetime import datetime, timedelta

from app import schema
from app.models import base
from app.models.provider_creds import ProviderCreds
from app.models.task import Task
from app.service import TaskService, session_manager
from app.service.event_service import EventService
from app.utils import enum
from app.wrapper.process_request import ProcessRequest
from app.utils.response_handler import ResponseHandler
from app.schema.response_integration_schema import ResponseIntegrationSchema
from app.service.payment_service import PaymentService
from app.models.base import (FeatureUrlPath,
                             Provider, PushPayment, SubTask,
                             Sessions, ConnectParkinglot)
from app.schema import TaskCreateSchema, session_schema
from app.config import settings
from app.utils.common import DateTimeUtils, build_task_from_event
from app.utils.data_filter import DataFilter
from app.service.privilege_permit import PrivilegePermit
import traceback
from app.utils.sg_admin_apis import SGAdminApis

logger = logging.getLogger(__name__)


class CheckReservationByLPR:

    @staticmethod
    def check_reservation_by_lpr(db, task, sub_tasks):
        connect_parkinglot = ConnectParkinglot.get_connect_parking_lot_id(db, task.parking_lot_id)
        session = Sessions.get_session_by_id(db, task.session_id)

        # check LPR privilege permit
        privilege_permit = PrivilegePermit.check_privilege_permit(db, connect_parkinglot, task)
        
        # close sub-tasks and return without checking its payment
        if privilege_permit:
            SubTask.close_sub_task_with_task_id(db, [task.id])

            # when a car have expiry for privilige permit, then task will process after that expiry
            if privilege_permit['expiry_at']:
                build_task_from_event(db, task, DateTimeUtils.convert_to_iso_format(privilege_permit['expiry_at']))

            Sessions.update_is_waiting_for_payment(db, session)
            return

        lpr_matching_threshold_distance = 0
        with SGAdminApis() as sgadmin:
            lot_status = sgadmin.lot_status(db, task.parking_lot_id)
            if lot_status:
                lpr_matching_threshold_distance = lot_status['lpr_number_plate_text_matching_distance_thresh']

        for sub_task in sub_tasks:
            feature_by_id = FeatureUrlPath.get_feature_url_path_by_id(db, sub_task.feature_url_path)
            provider_creds_obj = ProviderCreds.get_by_id(db, sub_task.provider_creds_id)

            data = ProcessRequest.process(db=db,
                                        task=task,
                                        sub_task=sub_task,
                                        feature=feature_by_id,
                                        provider_creds=provider_creds_obj,
                                        connect_parkinglot=connect_parkinglot)

            json_response_schema = json.loads(feature_by_id.response_schema)

            data = ResponseHandler.replace_json_values_v2(data, json_response_schema)
            if data is not None:
                results = DataFilter.filter(provider_creds_obj.text_key, task, data, lpr_matching_threshold_distance)
                if results is not None:

                    response_schema = ResponseIntegrationSchema(
                        price_paid=results.get("price_paid"),
                        paid_date=results.get("paid_date"),
                        expiry_date=results.get("expiry_date"),
                        provider=results.get("provider"),
                        station_price=results.get("station_price"),
                        station_name=results.get("station_name"),
                        plate_number=task.plate_number,
                        matched_plate_number=results.get("plate_number"),
                        lpr_match_number=lpr_matching_threshold_distance,
                        action_type=json_response_schema['action_type'] if 'action_type' in json_response_schema else ""
                    )

                    timestamp = results['expiry_date']
                    PaymentService.paid(db, task, sub_task, response_schema,
                                        timestamp=timestamp)
                    Task.close_task_with_session_id(db, task.session_id)
                    SubTask.close_sub_task_on_paid(db, sub_task.id, task.id)

                    if task.event_type != enum.Event.lpr_exit.value:
                        build_task_from_event(db, task, timestamp)
                        logger.debug(
                            f"Task: {task.id} / LPR: {Task.plate_number} - Task completed. New task created")
                        return response_schema

            SubTask.close_sub_task(db, sub_task.id)

        exits = task.session_contains_both_rp(db, task.session_id, "payment")
        if not exits:
            handle_not_paid_and_task_creation(task=task, db=db, sub_tasks=sub_tasks)
        else:
            # action type should be Unreserved first time
            is_last_reserved = base.SessionLog.check_last_session_by_action_type(db, task.session_id, [
                enum.EventsForSessionLog.reservation_remaining.value, enum.EventsForSessionLog.monthly_pass.value])
            action_type = enum.EventsForSessionLog.reservation_expired.value if is_last_reserved else enum.EventsForSessionLog.unreserved.value

            session_manager.SessionManager.create_session_logs(db=db,
                                                            session_id=task.session_id,
                                                            action_type=action_type,
                                                            description=action_type
                                                            )


def handle_not_paid_and_task_creation(task, db, sub_tasks):

    # action type should be Unreserved first time
    is_last_reserved = base.SessionLog.check_last_session_by_action_type(db, task.session_id, [
        enum.EventsForSessionLog.reservation_remaining.value, enum.EventsForSessionLog.monthly_pass.value])
    action_type = enum.EventsForSessionLog.reservation_expired.value if is_last_reserved else enum.EventsForSessionLog.unreserved.value

    sgadmin_alerts_ids = PaymentService.not_paid(task=task, db=db,
                                                 action_type=action_type,
                                                 violation_type=enum.EventTypes.PAYMENT_VIOLATION.value,
                                                 violation_flag=True)
    if sgadmin_alerts_ids is None:
        setattr(task, "sgadmin_alerts_ids", task.sgadmin_alerts_ids)

    timestamp = datetime.utcnow() + timedelta(minutes=settings.VIOLATION_GRACE_PERIOD)

    session = Sessions.get_session_by_id(db, task.session_id)
    connect_parking_lot_id = ConnectParkinglot.get_connect_parking_lot_id(db, task.parking_lot_id)
    session_manager.SessionManager.create_session_logs(db=db,
                                                       session_id=task.session_id,
                                                       action_type=action_type,
                                                       description=action_type
                                                       )
    if session and connect_parking_lot_id is not None:
        if session.not_paid_counter < connect_parking_lot_id.retry_mechanism:
            if task.event_type != "car.exit":
                build_task_from_event(db, task, timestamp)
                logger.debug(
                    f"Task: {task.id} / LPR: {task.plate_number} - Task completed. New task created with Id: {task.id}")
                session_manager.SessionManager.update_counter(db, task.session_id, enum.ActionType.NOT_PAID.value)
