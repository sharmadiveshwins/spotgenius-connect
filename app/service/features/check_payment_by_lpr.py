import json
import logging
from app.models.provider_creds import ProviderCreds
from app.utils import enum
from app.wrapper.process_request import ProcessRequest
from app.utils.response_handler import ResponseHandler
from app.schema.response_integration_schema import ResponseIntegrationSchema
from app.service.payment_service import PaymentService
from app.models.base import (FeatureUrlPath, Violation,
                             Provider, SubTask,
                             Sessions, ConnectParkinglot)

from app.utils.common import DateTimeUtils, build_task_from_event
from app.service.privilege_permit import PrivilegePermit
from app.utils.data_filter import DataFilter
from app.utils.parking_window import ParkingWindow
from app.utils.violation_rule import ViolationRule
from datetime import datetime, timedelta
from app.models import base
from app.utils.sg_admin_apis import SGAdminApis
from app.service.payment_microservice import PaymentMicroService

logger = logging.getLogger(__name__)


class CheckPaymentByLPR:

    @staticmethod
    def check_payment_by_lpr(db, task, sub_tasks):

        # global timestamp
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

        # check current window is paid/free
        payment_window  = ParkingWindow.check_payment_window(connect_parkinglot)

        if "status" in payment_window and payment_window["status"]:
            # close overstay violation, window is switching from non-payment to payment
            reason = enum.AlertInactiveReason.FREE_TO_PAYMENT_WINDOW.value
            ViolationRule.close_overstay_violation(db, task, reason)

            lpr_matching_threshold_distance = 0
            with SGAdminApis() as sgadmin:
                lot_status = sgadmin.lot_status(db, task.parking_lot_id)
                if lot_status:
                    lpr_matching_threshold_distance = lot_status['lpr_number_plate_text_matching_distance_thresh']

            for sub_task in sub_tasks:
                feature_by_id = FeatureUrlPath.get_feature_url_path_by_id(db, sub_task.feature_url_path)
                provider_creds_obj = ProviderCreds.get_by_id(db, sub_task.provider_creds_id)
                provider_obj = Provider.get_provider_by_id(db, provider_creds_obj.provider_id)

                json_response_schema = json.loads(feature_by_id.response_schema)

                results = None
                if provider_obj.provider_api_request_type != enum.ProviderApiRequestType.Connect.value:
                    results = PaymentMicroService.check_payment(
                        db=db,
                        provider_cred=provider_creds_obj,
                        parking_lot_id=task.parking_lot_id,
                        grace_period=connect_parkinglot.grace_period,
                        api_request_endpoint=provider_obj.api_request_endpoint,
                        lpr_matching_threshold_distance=lpr_matching_threshold_distance,
                        feature=enum.PaymentServiceFeature.LPR.value,
                        task=task,
                        provider_text_key=provider_obj.text_key
                    )

                    valid_permit = enum.EventsForSessionLog.Valid_PERMIT.value

                    if not results and json_response_schema.get('action_type') == valid_permit:
                        is_permit = True

                        is_valid_to_show_permit_expired = base.SessionLog.check_last_session_by_action_type(
                            db,
                            task.session_id,
                            [valid_permit]
                        )

                        if is_permit and is_valid_to_show_permit_expired:
                            payment_window['action_type'] = enum.EventsForSessionLog.PERMIT_EXPIRED.value

                else:
                    provider_json_response = ProcessRequest.process(db=db,
                                                task=task,
                                                sub_task=sub_task,
                                                feature=feature_by_id,
                                                provider_creds=provider_creds_obj,
                                                connect_parkinglot=connect_parkinglot)

                    if provider_json_response:
                        replaced_response = ResponseHandler.replace_json_values_v2(provider_json_response, json_response_schema)
                        if replaced_response is not None:
                            results = DataFilter.filter(provider_creds_obj.text_key, task, replaced_response, lpr_matching_threshold_distance)

                if results is not None:
                    if provider_obj.text_key == enum.ProviderTextKey.Arrive.value:
                        base.PushPayment.update_payment_status(db, results['push_payment_id'])

                    # amount, start_timestamp, end_timestamp and match_lpr getting from payment service
                    response_schema = ResponseIntegrationSchema(
                        price_paid=results.get("price_paid", results.get("amount")),
                        paid_date=results.get("paid_date", results.get("start_timestamp")),
                        expiry_date=results.get("expiry_date", results.get("end_timestamp")),
                        provider=results.get("provider"),
                        station_price=results.get("station_price"),
                        station_name=results.get("station_name"),
                        plate_number=task.plate_number,
                        matched_plate_number=results.get("match_lpr"),
                        lpr_match_number=lpr_matching_threshold_distance,
                        action_type=json_response_schema['action_type'] if 'action_type' in json_response_schema else ""
                    )

                    is_payment_found = task.sg_event_response.get(
                        "entry_time") and task.sg_event_response.get(
                        "entry_time") > response_schema.paid_date
                    session_exists = Sessions.get_today_session_with_plate(db, task.plate_number,
                                                                            task.parking_lot_id)
                    if response_schema and (response_schema.expiry_date or response_schema.price_paid):

                        timestamp = response_schema.expiry_date

                        if connect_parkinglot.is_in_out_policy:
                            return CheckPaymentByLPR.process_payment(db, task, sub_task, provider_obj, timestamp,
                                                    response_schema)

                        elif is_payment_found and session_exists:
                            logger.info(
                                f"Task: {task.id} / LPR: {task.plate_number} - Payment not found for {provider_obj.name}")
                        else:
                            return CheckPaymentByLPR.process_payment(db, task, sub_task, provider_obj, timestamp,
                                                    response_schema)
                    else:
                        logger.info(
                            f"Task: {task.id} / LPR: {task.plate_number} - Payment not found for {provider_obj.name}")
                # elif "expiry_date" in results and results["expiry_date"] is not None:
                #     logger.info(
                #         f"Task: {task.id} / LPR: {task.plate_number} - Payment found for {provider_obj.name} but expired on {results.get('expiry_date')}")
                else:
                    logger.info(
                        f"Task: {task.id} / LPR: {task.plate_number} - Payment not found for {provider_obj.name}")

                SubTask.close_sub_task(db, sub_task.id)

        elif "status" in payment_window and not payment_window["status"]:
            # close payment violation, window is switching from payment to non-payment
            reason = "Window is switching from payment to non-payment"
            ViolationRule.close_payment_violation(db, task, reason)
            # TODO ensure that task is getting created for inactivation
            from app.service.event_service import EventService
            check_for_inactivation_feature = Violation.check_for_inactivation_feature(db,
                                                                                       parking_lot_id=task.parking_lot_id,
                                                                                       session_id=task.session_id)
            if check_for_inactivation_feature:
                EventService.execute_event_for_inactivation_task(db, task.sg_event_response)

        ViolationRule.manage_free_window_and_not_paid_task(db, task, connect_parkinglot, session, payment_window)

    @staticmethod
    def process_payment(db, task, sub_task, provider_obj, timestamp, response_schema):
        logger.info(
            f"Task: {task.id} / LPR: {task.plate_number} - Payment found for {provider_obj.name} Until {timestamp}")
        PaymentService.paid(db, task, sub_task, response_schema, timestamp=timestamp)
        SubTask.close_sub_task_on_paid(db, sub_task.id, task.id)

        if task.event_type != enum.Event.lpr_exit.value:
            build_task_from_event(db, task, timestamp)
            logger.debug(f"Task: {task.id} / LPR: {task.plate_number} - Task completed. New task created")
        return response_schema

    # @staticmethod
    # def handle_permit_check(db, task, results, json_response_schema, payment_window):
    #
    #     valid_permit = enum.EventsForSessionLog.Valid_PERMIT.value
    #     is_permit_check_required = (not results or not results.get('end_timestamp')
    #                                 and json_response_schema.get('action_type') == valid_permit)
    #
    #     if not is_permit_check_required:
    #         return
    #
    #     is_only_paris_connected = base.ProviderConnect.is_only_paris_connected(
    #         db,
    #         task.parking_lot_id,
    #         "inteapark.paris",
    #         "provider.payment"
    #     )
    #
    #     is_valid_to_show_permit_expired = base.SessionLog.check_last_session_by_action_type(
    #         db,
    #         task.session_id,
    #         [valid_permit]
    #     )
    #
    #     if is_only_paris_connected and is_valid_to_show_permit_expired:
    #         payment_window['action_type'] = "Permit Expired"