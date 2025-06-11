from app.models import base
from datetime import datetime
from app.utils.common import build_task_from_event
from app.service import session_manager
from app.utils import enum
from app.models.provider_types import ProviderTypes
from app.models.task import Task

from app import schema
from app.service.alert_service import AlertSgadmin
from app.utils.common import car_identification_log
from app.models.violation import Violation
from app.utils.sg_admin_apis import SGAdminApis

import logging

logger = logging.getLogger(__name__)


class ViolationRule:
    @staticmethod
    def check_remaining_time(check_from, end_time) -> str:
        time_diff = end_time - check_from
        remaining_minutes = time_diff.total_seconds() / 60

        if remaining_minutes > 60:
            hours = remaining_minutes / 60
            return f"{hours:.2f} Hr"
        else:
            return f"{max(0, abs(remaining_minutes)):.0f} Min"

    @staticmethod
    def manage_free_window_and_not_paid_task(db, task, connect_parkinglot, session, payment_window):
        try:
            window_status, next_at, end_time = payment_window['status'], payment_window['next_at'], payment_window['end_time']
            has_nph_task, violation_flag = False, False

            if window_status:
                action_type = enum.EventsForSessionLog.not_paid.value if not payment_window.get('action_type') else \
                payment_window['action_type']
                violation_type = enum.EventTypes.PAYMENT_VIOLATION.value
                violation_flag = True
            else:
                if not session.has_nph_task:
                    has_nph_task = True
                    remaining_time = ViolationRule.check_remaining_time(datetime.utcnow(), next_at)
                    action_type = enum.EventsForSessionLog.non_payment_time.value + ":" + remaining_time
                else:
                    violation_flag = True
                    next_at = end_time
                    action_type = enum.EventsForSessionLog.overstay.value

                violation_type = enum.EventTypes.OVERSTAY_VIOLATION.value

            from app.service.payment_service import PaymentService
            PaymentService.not_paid(
                task=task,
                db=db,
                action_type=action_type,
                violation_type=violation_type,
                violation_flag=violation_flag
            )

            attributes_to_update = {
                "is_waiting_for_payment": False,
                "has_nph_task": has_nph_task
            }

            session_manager.SessionManager.create_session_logs(
                db=db,
                attributes_dict=attributes_to_update,
                session_id=task.session_id,
                action_type=action_type,
                action="UPDATE",
                description=action_type
            )
            logger.debug(f'Task: {task.id} / LPR: {task.plate_number} / SPOT Name: {task.parking_spot_name}'
                         f' / Session log is created for: {action_type.capitalize()} / session id: {task.session_id}')

            if violation_flag:
                logger.debug(f'{action_type} violation found for plate number {task.plate_number}')

                # To avoid creation of new task after overstay violation, when lot is always free
                if connect_parkinglot.parking_operations == enum.ParkingOperations.lpr_based_24_hours_free_parking.value:
                    return

            if session and connect_parkinglot is not None:
                if (not window_status
                        or session.not_paid_counter < connect_parkinglot.retry_mechanism):
                    if task.event_type != enum.EventTypes.CAR_EXIT.value:
                        build_task_from_event(db, task, next_at)
                        logger.debug(f"Task: {task.id} / LPR: {task.plate_number} - Task completed. New task created")
                        session_manager.SessionManager.update_counter(db, task.session_id, enum.ActionType.NOT_PAID.value)

        except Exception as e:
            logger.error(str(e))

    @staticmethod
    def close_overstay_violation(db, task, reason):
        provider_type = db.query(ProviderTypes).filter(ProviderTypes.text_key == enum.ProviderTypes.PROVIDER_VIOLATION.value).first()
        opened_violation_task = Task.get_pending_overstay_violation(db, provider_type.id, task.session_id)

        if opened_violation_task:
            from app.service.event_service import EventService
            check_for_inactivation_feature = Violation.check_for_inactivation_feature(db,
                                                                                      parking_lot_id=task.parking_lot_id,
                                                                                      session_id=task.session_id)
            if check_for_inactivation_feature:
                EventService.execute_event_for_inactivation_task(db, task.sg_event_response)


        alert_id_list = opened_violation_task.sgadmin_alerts_ids if opened_violation_task else None

        if alert_id_list:
            violation_type = enum.EventTypes.OVERSTAY_VIOLATION.value
            violation_action_type = enum.EventsForSessionLog.OVERSTAY_ALERT_CLOSED.value
            ViolationRule.close_violation(db, alert_id_list, opened_violation_task, task, violation_type, violation_action_type, reason)

    @staticmethod
    def close_payment_violation(db, task, reason):
        provider_type = db.query(ProviderTypes).filter(ProviderTypes.text_key == enum.ProviderTypes.PROVIDER_VIOLATION.value).first()
        opened_violation_task = base.Task.get_pending_payment_violation(db, provider_type.id, task.session_id)
        alert_id_list = opened_violation_task.sgadmin_alerts_ids if opened_violation_task else None

        if alert_id_list:
            violation_type = enum.EventTypes.PAYMENT_VIOLATION.value
            violation_action_type = enum.EventsForSessionLog.PAYMENT_ALERT_CLOSED.value
            ViolationRule.close_violation(db, alert_id_list, opened_violation_task, task, violation_type, violation_action_type, reason)


    @staticmethod
    def close_violation(db, alert_id_list, opened_violation_task, task, violation_type, violation_action_type, reason):
        for alert_id in alert_id_list:
            alert_update_schema = schema.AlertUpdateSchema(id=alert_id, alert_state="open",
                                                            alert_trigger_state="inactive",
                                                           inactive_reason=reason)
            AlertSgadmin.update_alert(alert_update_schema)

            # Update status to closed in task table
            base.Task.update_alert_status(db, opened_violation_task, enum.ViolationStatus.CLOSED.value)

            # Add session log for Alert Closed only when if last alert was sent
            session_manager.SessionManager.create_session_logs(db,
                                                                session_id=task.session_id,
                                                                action_type=violation_action_type,
                                                                description=violation_action_type)

            # car_identification for dynamically showing logs for LPR or Spot based
            car_identification = car_identification_log(task)

            violation = Violation.get_violation_by_session_id(db, task.session_id, violation_type=violation_type)
            if violation is not None:
                Violation.update_status(db, violation.id, "CLOSE")
                logger.info(
                    f"Task: {task.id} / {car_identification} - Violation inactivated with Id: {violation.id} / Alert: {alert_id}")
            else:
                logger.info(
                    f"Task: {task.id} / {car_identification} - Violation inactivated. Alert: {alert_id}")

    @staticmethod
    def lpr_exit_status(db, parking_lot_id, lpr_record_id):
        is_lpr_exited = False

        try:
            lpr_status_reposnse = SGAdminApis().lpr_exit_status(db, parking_lot_id, lpr_record_id)
            if lpr_status_reposnse:
                is_lpr_exited = lpr_status_reposnse["lpr_exited"]
        except Exception as e:
            logger.error(f"Error in checking lpr exit status: {str(e)}")

        return is_lpr_exited

    @staticmethod
    def spot_free_status(db, parking_lot_id, spot_name):
        is_spot_free = False

        try:
            spot_status_response = SGAdminApis().spot_status(db, parking_lot_id, spot_name)
            if spot_status_response and not spot_status_response["is_unknown"] and spot_status_response["spot_status"] in ("available", "free"):
                is_spot_free = True
        except Exception as e:
            logger.error(f"Error in checking spot status: {str(e)}")

        return is_spot_free
