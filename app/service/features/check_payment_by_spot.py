import json
import logging
from app.models.provider_creds import ProviderCreds
from app.utils import enum
from app.wrapper.process_request import ProcessRequest
from app.utils.response_handler import ResponseHandler
from app.schema.response_integration_schema import ResponseIntegrationSchema
from app.service.payment_service import PaymentService
from app.models.base import (FeatureUrlPath,
                             Provider, SubTask,
                             Sessions, ConnectParkinglot)

from app.utils.common import DateTimeUtils, build_task_from_event
from app.utils.parking_window import ParkingWindow
from app.utils.violation_rule import ViolationRule
from datetime import datetime

logger = logging.getLogger(__name__)


class CheckPaymentBySpot:

    @staticmethod
    def check_payment_by_spot(db, task, sub_tasks):
        connect_parkinglot = ConnectParkinglot.get_connect_parking_lot_id(db, task.parking_lot_id)
        session = Sessions.get_session_by_id(db, task.session_id)
        
        # Reserved spot, payment should not be checked and new task should not be created for payment check
        if (
            task.sg_event_response.get("disable_spot_payment")
            and (connect_parkinglot.parking_operations == enum.ParkingOperations.paid_24_hours.value
                 or connect_parkinglot.parking_operations == enum.ParkingOperations.spot_based_24_hours_free_parking.value)
        ):
            logger.debug(
                f"Task: {task.id} / SPOT: {task.parking_spot_id} - disable spot payment - "
                f"parking operation: {connect_parkinglot.parking_operations}"
            )
            SubTask.close_sub_task_with_task_id(db, [task.id])
            return


        # check current window is paid/free. In spot based payment check there would be no free window
        payment_window  = ParkingWindow.check_payment_window(connect_parkinglot)

        # if "status" in payment_window and payment_window["status"]:
        # if connect_parkinglot.parking_operations == enum.ParkingOperations.specify_lpr_based_paid_parking_time.value:

            # close overstay violation, window is switching from non-payment to payment
            # reason = enum.AlertInactiveReason.FREE_TO_PAYMENT_WINDOW.value
            # ViolationRule.close_overstay_violation(db, task, reason)

        for sub_task in sub_tasks:
            feature_by_id = FeatureUrlPath.get_feature_url_path_by_id(db, sub_task.feature_url_path)
            provider_creds_obj = ProviderCreds.get_by_id(db, sub_task.provider_creds_id)
            provider_obj = Provider.get_provider_by_id(db, provider_creds_obj.provider_id)

            data = ProcessRequest.process(db=db,
                                        task=task,
                                        sub_task=sub_task,
                                        feature=feature_by_id,
                                        provider_creds=provider_creds_obj,
                                        connect_parkinglot=connect_parkinglot)

            json_response_schema = json.loads(feature_by_id.response_schema)
            if data is not None:
                results = ResponseHandler.replace_json_values(data, json_response_schema)

                if results is not None:

                    if 'paid_date' in results:
                        results['paid_date'] = DateTimeUtils.convert_to_iso_format(results['paid_date'])
                    if 'expiry_date' in results:
                        results['expiry_date'] = DateTimeUtils.convert_to_iso_format(results['expiry_date'])

                    check_payment_expiration = DateTimeUtils.is_future_date(
                        results.get("expiry_date", "1990-01-01 12:00:00"))
                    if check_payment_expiration:
                        response_schema = ResponseIntegrationSchema(
                            price_paid=results.get("price_paid"),
                            paid_date=results.get("paid_date"),
                            expiry_date=results.get("expiry_date"),
                            provider=results.get("provider"),
                            station_price=results.get("station_price"),
                            station_name=results.get("station_name"),
                            parking_spot_id=results.get("spot_id"),
                            action_type=json_response_schema['action_type'] if 'action_type' in json_response_schema else ""
                        )

                        if response_schema and (response_schema.expiry_date or response_schema.price_paid):
                            timestamp = response_schema.expiry_date
                            logger.info(
                                f"Task: {task.id} / SPOT: {task.parking_spot_id} - Payment found for {provider_obj.name} Until {timestamp}")

                            PaymentService.paid(db, task, sub_task, response_schema, timestamp=timestamp)
                            SubTask.close_sub_task_on_paid(db, sub_task.id, task.id)

                            if task.event_type != enum.Event.lpr_exit.value:
                                build_task_from_event(db, task, timestamp)
                                logger.debug(
                                    f"Task: {task.id} / SPOT: {task.parking_spot_id} - Task completed. New task created with Id: {task.id}")
                            return response_schema

                        else:
                            logger.info(
                                f"Task: {task.id} / SPOT: {task.parking_spot_id} - Payment not found for {provider_obj.name}")
                    elif "expiry_date" in results and results["expiry_date"] is not None:
                        logger.info(
                            f"Task: {task.id} / SPOT: {task.parking_spot_id} - Payment found for {provider_obj.name} but expired on {results.get('expiry_date')}")
                else:
                    logger.info(
                        f"Task: {task.id} / SPOT: {task.parking_spot_id} - Payment not found for {provider_obj.name}")

            SubTask.close_sub_task(db, sub_task.id)

        # elif "status" in payment_window and not payment_window["status"]:
        #     # close payment violation, window is switching from payment to non-payment
        #     reason = "Window is switching from payment to non-payment"
        #     ViolationRule.close_payment_violation(db, task, reason)

        ViolationRule.manage_free_window_and_not_paid_task(db, task, connect_parkinglot, session, payment_window)
