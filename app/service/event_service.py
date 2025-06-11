import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional

from sqlalchemy.orm import Session
from app.models.base import ProviderConnect
from app.models.base import ConnectParkinglot
from app.models import base
from app.schema import TaskSchema, TaskCreateSchema
from app import schema
from app.utils import enum
from sqlalchemy import case, or_

logger = logging.getLogger(__name__)


def custom_encoder(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return str(obj)


class EventService:

    @staticmethod
    def execute_event(events, db: Session, timestamp: Optional[datetime] = None):
        """
        function to create new event instances populating the details received via API request data
        """

        global new_task
        success_events = []
        failure_events = []
        task_id = None
        description = None
        # Group events by parking lot id
        grouped_parking_lot = defaultdict(list)
        for event in events:
            combination_key = event.parking_lot_id
            grouped_parking_lot[combination_key].append(event)

        normalize_events = []
        sg_event_response_data = None
        for parking_lot_id, events in grouped_parking_lot.items():
            parking_connect_obj = ConnectParkinglot.get_connect_parking_lot_id(db, parking_lot_id)
            if parking_connect_obj:
                result_dict = {'task': []}

                from app.utils.parking_window import ParkingWindow
                payment_window = ParkingWindow.check_payment_window(parking_connect_obj)

                for event in events:
                    providers_connects = ProviderConnect.find_providers_by_event_type_and_lot(db, event,
                                                                                              parking_connect_obj.id)


                    if not providers_connects and event.event_key not in enum.SpotLprEventsMapping.EXIT.value:
                        logger.debug(f'Execute event : {event.event_key} / not in exit / Provider Connects: False')
                        return failure_events.append({"event": event, "reason": "No providers found"})
                    if not providers_connects and event.event_key in enum.SpotLprEventsMapping.EXIT.value:
                        logger.debug(f'Execute event : {event.event_key} / in exit / Provider Connects: False')
                        if event.manually_triggered:
                            description = enum.EventsForSessionLog.Forced_Exit_Description.value
                            inactive_reason = enum.AlertInactiveReason.FORCED_EXIT.value
                        else:
                            inactive_reason = enum.AlertInactiveReason.EXIT_DETECT.value
                        return EventService.handle_unavailable_provider_exit(db=db,
                                                                             event=event,
                                                                             reason=inactive_reason,
                                                                             description=description
                                                                             )

                    for feature_key, providers in providers_connects.items():
                        split_feature = feature_key.split('.')[0].strip()
                        get_provider_type = db.query(base.ProviderTypes).filter(base.ProviderTypes.name.ilike(
                            f'{split_feature}%')).first()

                        json_data = json.dumps(event.__dict__, default=custom_encoder)
                        sg_event_response_data = json.loads(json_data)

                        from app.utils.common import next_at_for_task
                        timestamp = next_at_for_task(event=event,
                                                     parking_connect_obj=parking_connect_obj,
                                                     timestamp=timestamp,
                                                     payment_window=payment_window
                                                     )

                        new_event = TaskSchema(
                            parking_lot_id=event.parking_lot_id,
                            event_type=event.event_key,
                            next_at=timestamp,
                            provider_type=get_provider_type.id,
                            feature_text_key=feature_key,
                            plate_number=event.license_plate if event.license_plate else None,
                            parking_spot_id=str(event.parking_spot_id) if event.parking_spot_id else None,
                            parking_spot_name=str(event.parking_spot_name) if event.parking_spot_name else None,
                            sg_event_response=sg_event_response_data,
                            session_id=event.session_id,
                            sgadmin_alerts_ids=event.sgadmin_alerts_ids,
                            state=event.region
                        )

                        for provider_connect in providers:
                            if feature_key in provider_connect['text_key']:
                                new_event.providers_connects = providers

                        result_dict['task'].append(new_event)
                normalize_events.append(result_dict)

        for data in normalize_events:
            for task in data.get('task'):
                from app.service.task_service import TaskService
                sub_tasks = task.providers_connects

                if task.event_type in enum.SpotLprEventsMapping.EXIT.value:
                    inactive_reason = "LPR exit is detected for the car"
                    EventService.close_alert(db, task, inactive_reason)

                task.sg_event_response = sg_event_response_data
                task_create_schema = TaskCreateSchema(**task.dict())

                # move this code to up so that session log create before task
                action_type = enum.EventsForSessionLog[
                task.event_type.split('.')[1] if '.' in task.event_type else task.event_type].value.upper()
                is_entry_exists = base.SessionLog.check_if_entry_or_exit_associate_with_session(db, task.session_id,
                                                                                                action_type)
                attribute_to_update = {}
                if not payment_window['status'] and task.event_type in (enum.EventTypes.SPOT_OCCUPIED.value, enum.EventTypes.CAR_ENTRY.value):
                    attribute_to_update = {"is_waiting_for_payment": False}
                elif task.event_type in enum.EventTypes.GROUPED_EVENTS.value and not task.sg_event_response["disable_spot_payment"]:
                    attribute_to_update = {"is_waiting_for_payment": enum.IsWaitingForPaymentMapping[action_type].value}

                create_session = (
                        not is_entry_exists
                        and task.event_type != enum.EventTypes.PAYMENT_VIOLATION.value
                        and task.event_type != enum.EventTypes.OVERSTAY_VIOLATION.value
                        and task.event_type != enum.EventTypes.PARKING_VIOLATION.value
                        and task.event_type != enum.EventTypes.VIOLATION_INACTIVE.value
                )
                if create_session:
                    from app.service.session_manager import SessionManager
                    description = action_type.capitalize() if description is None else description
                    SessionManager.create_session_logs(db=db,
                                                    attributes_dict=attribute_to_update,
                                                    action="UPDATE",
                                                    session_id=task.session_id,
                                                    action_type=action_type.capitalize(),
                                                    description=description,
                                                    event_at=events[0].timestamp
                                                    )

                    logger.debug(
                        f'Execute event: {task.event_type} / LPR: {task.plate_number} / SPOT Name: {task.parking_spot_name}'
                        f' / Session log is created for: {action_type.capitalize()} / session id: {task.session_id}'
                    )

                new_task = TaskService.create_task(db, task_create_schema, sub_tasks)
                logger.debug(
                    f'Execute event: {new_task.event_type} / LPR: {task.plate_number} / SPOT Name: {task.parking_spot_name}'
                    f'  / new task created with Task Id: {new_task.id} / session id: {task.session_id}'
                )

                task_id = new_task.id
                success_events.append(new_task)

        response_message = {
            "success_events": len(success_events),
            "failure_events": len(failure_events),
            "task_id": task_id
        }

        logger.debug(f'Execute event: {task.event_type} / response: {response_message}')

        return response_message

    @staticmethod
    def handle_unavailable_provider_exit(db, event, reason, description):
        success_events = []
        failure_events = []
        json_data = json.dumps(event.__dict__, default=custom_encoder)
        sg_event_response_data = json.loads(json_data)
        exit_event = TaskSchema(
            parking_lot_id=event.parking_lot_id,
            event_type=event.event_key,
            next_at=event.timestamp,
            provider_type=1,
            feature_text_key="NA",
            plate_number=event.license_plate,
            parking_spot_id=event.parking_spot_id,
            sg_event_response=sg_event_response_data,
            session_id=event.session_id,
            state=event.region
        )
        task_create_schema = TaskCreateSchema(**exit_event.dict())
        # TODO inactivation alert
        # TODO ensure that task is getting created for inactivation
        check_for_inactivation_feature = base.Violation.check_for_inactivation_feature(db,
                                                                                       parking_lot_id=event.parking_lot_id,
                                                                                       session_id=event.session_id)
        if check_for_inactivation_feature:
            EventService.execute_event_for_inactivation_task(db, event)
        task = base.Task.create_task(db, task_create_schema)

        logger.debug(
            f'Execute event: {task.event_type} / LPR: {task.plate_number} / SPOT Name: {task.parking_spot_name}'
            f' / New task is created with Task id: {task.id} / session id: {task.session_id}'
        )

        EventService.close_alert(db, task, reason)
        success_events.append(task)

        from app.service.session_manager import SessionManager
        action_type = enum.EventsForSessionLog[
            task.event_type.split('.')[1] if '.' in task.event_type else task.event_type].value.upper()

        if event.manually_triggered and event.event_key in enum.SpotLprEventsMapping.EXIT.value:
            action_type = enum.ActionType.SYSTEM_CLOSED.value
        SessionManager.create_session_logs(db=db,
                                           session_id=event.session_id,
                                           action_type=action_type.capitalize(),
                                           description=action_type.capitalize() if description is None else description,
                                           event_at=event.timestamp
                                           )
        logger.debug(
            f'Execute event: {task.event_type} / LPR: {task.plate_number} / SPOT Name: {task.parking_spot_name}'
            f' / Session log is created for: {action_type.capitalize()} / session id: {task.session_id}'
        )

        return {
            "success_events": len(success_events),
            "failure_events": len(failure_events),
        }

    @staticmethod
    def close_alert(db, task, reason):
        from app.service.session_manager import SessionManager

        provider_type = db.query(base.ProviderTypes).filter(base.ProviderTypes.text_key == enum.ProviderTypes.PROVIDER_VIOLATION.value).first()
        opened_violation_task = db.query(base.Task).filter(
            base.Task.session_id == task.session_id,
            or_(base.Task.alert_status != enum.ViolationStatus.CLOSED.value, base.Task.alert_status.is_(None)),
            base.Task.provider_type == provider_type.id
        ).order_by(base.Task.id).all()



        if opened_violation_task:
            for violation_task in opened_violation_task:
                alert_id_list = violation_task.sgadmin_alerts_ids
                if alert_id_list:
                    for alert_id in alert_id_list:

                        alert_update_schema = schema.AlertUpdateSchema(id=alert_id, alert_state="open",
                                                                    alert_trigger_state="inactive",
                                                                       inactive_reason=reason)
                        from app.service.alert_service import AlertSgadmin

                        AlertSgadmin.update_alert(alert_update_schema)

                        action_type = enum.EventsForSessionLog.PAYMENT_ALERT_CLOSED.value
                        if violation_task.event_type == enum.EventTypes.OVERSTAY_VIOLATION.value:
                            action_type = enum.EventsForSessionLog.OVERSTAY_ALERT_CLOSED.value

                        SessionManager.create_session_logs(db,
                                                        session_id=task.session_id,
                                                        action_type=action_type,
                                                        description=action_type
                                                        )

                        base.Task.update_alert_status(db, violation_task, enum.ViolationStatus.CLOSED.value)

        task_obj = None
        if task.plate_number:
            task_obj = base.Task.get_task_car_exit(db, task.plate_number, task.parking_lot_id)
        elif task.parking_spot_id:
            task_obj = base.Task.get_task_spot_free(db, task.parking_spot_id, task.parking_lot_id)

        if task_obj:
            task.session_id = task_obj.session_id

    @staticmethod
    def execute_event_for_inactivation_task(db, event):
        if isinstance(event, dict):
            session_id = event.get('session_id', 0)
            license_plate = event.get('license_plate', 'N/A')
        else:
            session_id = getattr(event, 'session_id', 0)
            license_plate = getattr(event, 'plate_number', None)
            if not license_plate:
                license_plate = getattr(event, 'license_plate', 'N/A')

        # Logging
        logging.info(f"Creating inactivation task for LP {license_plate} with session ID {session_id}")

        try:
            session_by_id = base.Sessions.get_session_by_id(db, session_id)
            str_to_dict = session_by_id.entry_event if isinstance(session_by_id.entry_event, dict) else json.loads(
                session_by_id.entry_event)
            anpr_event_schema = schema.SgAnprEventSchema(**str_to_dict)
            attributes = {
                "event_key": enum.EventTypes.VIOLATION_INACTIVE.value,
                "session_id": session_by_id.id,
                "parking_spot_name": session_by_id.parking_spot_name,
                "parking_spot_id": session_by_id.spot_id
            }

            for attr, value in attributes.items():
                setattr(anpr_event_schema, attr, value)

            EventService.execute_event(events=[anpr_event_schema], db=db)

            logging.info(f"Inactivation task is created for session_id: {session_by_id.id}")

        except Exception as e:
            logging.error(f"Failed to execute inactivation event for session_id: {event.session_id}. Error: {str(e)}", exc_info=True)

    @staticmethod
    def close_session_tasks_and_alerts(db, session_id: int, alert_close_reason=''):
        task = base.Task.get_task_by_session_id(db, session_id)
        if task:
            EventService.close_alert(db, task, alert_close_reason)
            violations = base.Violation.get_all_violation_associate_with_session(db, task.session_id)
            if violations:
                for violation in violations:
                    base.Violation.update_status(db, violation.id, "CLOSE")

            base.Task.close_task_with_plate_number_and_session_id(db, task.parking_lot_id, task.plate_number, task.session_id)

            check_for_inactivation_feature = base.Violation.check_for_inactivation_feature(db,
                                                                                        parking_lot_id=task.parking_lot_id,
                                                                                        session_id=task.session_id)
            if check_for_inactivation_feature:
                EventService.execute_event_for_inactivation_task(db, task)

            db.commit()
