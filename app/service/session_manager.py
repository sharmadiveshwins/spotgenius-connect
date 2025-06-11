import json
from datetime import datetime
import logging
from typing import Any, Optional

import pytz
from fastapi import HTTPException
from app import schema
from sqlalchemy.orm import Session
from app.models import base
from app.models.task import Task
from app.models.violation import Violation
from app.service.event_service import EventService
from app.utils import enum
from app.utils.common import set_text_for_session_ui, fetch_violation_amount
from collections import defaultdict

logger = logging.getLogger(__name__)


class SessionManager:

    @staticmethod
    def create_session_audit(db: Session, events: schema.SgAnprEventSchema):

        try:
            # Check if parking lot exists
            parking_lot = base.ConnectParkinglot.get_connect_parking_lot_id(db, events.parking_lot_id)
            if not parking_lot:
                return f"No parking lot found with ID {events.parking_lot_id}"

            session_audit = schema.SgSessionAudit(
                parking_lot_id=events.parking_lot_id,
                lpr_number=events.license_plate,
                spot_id=events.parking_spot_id,
                parking_spot_name=events.parking_spot_name,
                session_start_time=events.timestamp
            )

            # Handle car entry event
            if events.event_key == enum.Event.lpr_entry.value:
                session_audit.lpr_record_id = events.lpr_record_id
                session_exist = SessionManager.check_session_on_car_entry(db,
                                                                          session_audit.lpr_number,
                                                                          session_audit.parking_lot_id)

                logger.debug(f'Handle event: {events.event_key} / LPR: {events.license_plate}')
                if session_exist:
                    attributes_to_update = {"is_active": False,
                                            "is_waiting_for_payment": False,
                                            }
                    base.Sessions.update_attributes_in_session_audit(db, session_exist.id, attributes_to_update)
                    base.Task.close_task_with_session_id(db, session_exist.id)
                    task = base.Task.get_task_by_session_id(db, session_exist.id)
                    reason = enum.AlertInactiveReason.SAME_LPR_ENTRY.value
                    if task:
                        EventService.close_alert(db, task, reason)
                    SessionManager.create_session_logs(db=db,
                                                       session_id=session_exist.id,
                                                       action_type=enum.ActionType.SYSTEM_CLOSED.value,
                                                       description=enum.EventsForSessionLog.LPR_Entry_Description.value
                                                       )

                session_audit.entry_event = events.json()
                session_id = base.Sessions.insert_sg_admin_events(db, session_audit).id
                events.session_id = session_id

                logger.debug(f'Handle event: {events.event_key} / LPR: {events.license_plate} / session id: {session_id}')
                return EventService.execute_event([events], db)

            # Handle car exit event
            if events.event_key == enum.Event.lpr_exit.value:
                session_audit.lpr_record_id = events.lpr_record_id
                session_audit.exit_event = events.json()
                session = base.Sessions.get_session_by_plate(db, events.license_plate, events.parking_lot_id)

                logger.debug(f'Handle event: {events.event_key} / LPR: {events.license_plate}')

                if session:
                    attributes_to_update = {"exit_event": events.json(), "is_waiting_for_payment": False}
                    updated_session = SessionManager.update_session_audit(db, session.id, attributes_to_update)
                    events.session_id = updated_session.id
                    logger.debug(f'Handle event: {enum.Event.lpr_exit.value} / LPR: {events.license_plate} / session id: {events.session_id}')
                else:
                    session_id = base.Sessions.insert_sg_admin_events(db, session_audit)
                    logger.debug(f'Handle event: {enum.Event.lpr_exit.value} / LPR: {session_id.lpr_number} / session id: {session_id.id}')

                return EventService.execute_event([events], db)

            # Handle spot updates event
            if events.event_key == enum.Event.parking_spot_updates.value and events.is_unknown == False:
                events.parking_spot_id = str(events.parking_spot_id)

                if events.spot_status == enum.Event.unavailable.name:
                    events.event_key = enum.Event.unavailable.value
                    session_exist = SessionManager.check_session_on_spot_occupied(db,
                                                                                  str(session_audit.spot_id),
                                                                                  session_audit.parking_lot_id)

                    logger.debug(f'Handle event: {events.event_key} / SPOT Name: {session_audit.parking_spot_name}')
                    if session_exist:
                        attributes_to_update = {"is_active": False,
                                                "is_waiting_for_payment": False,
                                                }
                        base.Sessions.update_attributes_in_session_audit(db, session_exist.id, attributes_to_update)
                        base.Task.close_task_with_session_id(db, session_exist.id)
                        reason = enum.AlertInactiveReason.SAME_OCCUPIED_EVENT.value
                        task = base.Task.get_task_by_session_id(db, session_exist.id)
                        if task:
                            EventService.close_alert(db, task, reason)
                        SessionManager.create_session_logs(db=db,
                                                           session_id=session_exist.id,
                                                           action_type=enum.ActionType.SYSTEM_CLOSED.value,
                                                           description=enum.EventsForSessionLog.Occupied_Description.value
                                                           )

                    session_audit.entry_event = events.json()
                    session_audit.is_waiting_for_payment = False if events.disable_spot_payment else None
                    session_id = base.Sessions.insert_sg_admin_events(db, session_audit).id
                    events.session_id = session_id

                    logger.debug(f'Handle event: {events.event_key} / SPOT Name: {session_audit.parking_spot_name} / session id: {session_id}')
                    return EventService.execute_event([events], db)

                if events.spot_status == enum.Event.available.name:
                    events.event_key = enum.Event.available.value
                    session_audit.exit_event = events.json()
                    session = base.Sessions.get_session_by_spot(db, str(events.parking_spot_id), events.parking_lot_id)

                    logger.debug(f'Handle event: {events.event_key} / SPOT Name: {session_audit.parking_spot_name}')
                    if session:
                        attributes_to_update = {"exit_event": events.json(), "is_waiting_for_payment": False}
                        updated_session = SessionManager.update_session_audit(db, session.id, attributes_to_update)
                        events.session_id = updated_session.id
                        logger.debug(f'Handle event: {enum.Event.available.name} / SPOT Name: {session_audit.parking_spot_name} / session id: {events.session_id}')
                    else:
                        session_id = base.Sessions.insert_sg_admin_events(db, session_audit).id
                        logger.debug(f'Handle event: {enum.Event.available.name} / SPOT Name: {session_audit.parking_spot_name} / session id: {session_id}')

                    return EventService.execute_event([events], db)

            if events.event_key == enum.Event.parking_violations.value:

                session = SessionManager.check_session_on_violation(db, events.parking_lot_id,
                                                                         events.license_plate, events.lpr_record_id)
                if session:
                    task = base.Task.fetch_spot_details_by_session_id(db, session.id)
                    if task and events.parking_spot_id is None:
                        events.parking_spot_id = task.parking_spot_id
                        events.parking_spot_name = task.parking_spot_name
                    events.session_id = session.id
                else:
                    session_audit.is_active = False
                    session = base.Sessions.insert_sg_admin_events(db, session_audit)
                    events.session_id = session.id
                response = EventService.execute_event([events], db)
                logger.info(f"fetching violation amount for alert id {events.alert_type_id}")
                violation_meta_data = fetch_violation_amount(db, events.parking_lot_id, events.alert_type_id)
                if response is not None:
                    violation = schema.Violation(
                                name=events.alert_title,
                                status="OPEN",
                                session="OPEN",
                                task_id=response.get("task_id", 0),
                                amount_due=violation_meta_data.get("amount"),
                                description=events.details,
                                plate_number=events.license_plate,
                                parking_spot_id=events.parking_spot_id,
                                parking_lot_id=events.parking_lot_id,
                                violation_type=events.event_key,
                                session_id=session.id,
                                meta_data=violation_meta_data,
                                violation_event=events.json(),
                                timestamp=events.timestamp

                             )

                    Violation.create_violation(db, violation)
                    return response
                return {"message": "not connected with any enforcement provider"}

            # Map the Spot id with the existing session whenever there's LPR to spot
            if events.event_key == enum.Event.lpr_to_spot.value:
                session_audit.lpr_record_id = events.lpr_record_id
                session_exist = SessionManager.check_session_to_map_lpr_to_spot(db,
                                                                          session_audit.lpr_number,
                                                                          session_audit.lpr_record_id)

                logger.debug(f'Handle event: {events.event_key} / LPR: {session_audit.lpr_number}')
                if session_exist:
                    attributes_to_update = {
                        "spot_id": session_audit.spot_id,
                        "parking_spot_name":session_audit.parking_spot_name
                    }
                    SessionManager.update_session_audit(db, session_exist.id, attributes_to_update)
                    if session_exist.is_lpr_to_spot:
                        sg_event_schema = schema.SgAnprEventSchema(**json.loads(session_exist.entry_event))
                        sg_event_schema.session_id = session_exist.id
                        sg_event_schema.parking_spot_id = session_audit.spot_id
                        sg_event_schema.parking_spot_name = session_audit.parking_spot_name
                        SessionManager.create_session_logs(db=db,session_id=session_exist.id,
                                                           action_type=enum.EventsForSessionLog.LPR_TO_SPOT.format(spot_name=session_audit.parking_spot_name),
                                                           description=f"LPR match to Spot name: {str(session_audit.parking_spot_name)}".title().replace('Lpr', 'LPR'),
                                                           event_at=events.timestamp
                                                           )
                        reason = enum.AlertInactiveReason.LPR_SPOT_DETECTED.value
                        EventService.close_session_tasks_and_alerts(db, session_exist.id, reason)
                        base.Sessions.update_attributes_in_session_audit(db, session_exist.id, {"has_nph_task": False})
                        return EventService.execute_event([sg_event_schema], db)
                    else:
                        SessionManager.create_session_logs(db=db,
                                                           session_id=session_exist.id,
                                                           action_type=enum.EventsForSessionLog.LPR_TO_SPOT.format(spot_name=session_audit.parking_spot_name),
                                                           description=f"LPR match to Spot name: {str(session_audit.parking_spot_name)}".title().replace('Lpr', 'LPR'),
                                                           event_at=events.timestamp
                                                           )

                        attributes_to_update = {"is_lpr_to_spot": True}
                        SessionManager.update_session_audit(db, session_exist.id, attributes_to_update)

                        Task.update_task_by_session_id(db, session_exist.id, session_audit.spot_id, events.parking_spot_name)
                        return {"message": "spot mapped to session"}

            # Handle lpr to spot free event
            if events.event_key == enum.Event.lpr_to_spot_free.value:
                session = base.Sessions.get_session_by_spot(db, str(events.parking_spot_id), events.parking_lot_id)
                if session:
                    SessionManager.create_session_logs(db=db, session_id=session.id,
                                                       action_type=enum.EventsForSessionLog.LPR_TO_SPOT_FREE.format(
                                                           spot_name=session_audit.parking_spot_name),
                                                       description=f"LPR match to Spot Free name: {str(session_audit.parking_spot_name)}".title().replace(
                                                           'Lpr', 'LPR'),
                                                       event_at=events.timestamp
                                                       )
                    reason = enum.AlertInactiveReason.LPR_TO_SPOT_FREE.value
                    EventService.close_session_tasks_and_alerts(db, session.id, reason)
                    attributes_to_update = {
                        "is_waiting_for_payment": False
                    }
                    SessionManager.update_session_audit(db, session.id, attributes_to_update)
                    return {"message": "spot free mapped to session"}

            if events.is_unknown:
                session_exist = SessionManager.check_session_on_spot_occupied(db,
                                                                              str(session_audit.spot_id),
                                                                              session_audit.parking_lot_id)

                if session_exist:
                    attributes_to_update = {"is_active": False,
                                            "is_waiting_for_payment": False,
                                            }
                    base.Sessions.update_attributes_in_session_audit(db, session_exist.id, attributes_to_update)
                    task_ids = base.Task.close_task_with_session_id(db, session_exist.id)
                    task = base.Task.get_task_by_session_id(db, session_exist.id)
                    reason = enum.AlertInactiveReason.UNKNOWN_EVENT.value
                    if task:
                        EventService.close_alert(db, task, reason)
                    SessionManager.create_session_logs(db=db,
                                                       session_id=session_exist.id,
                                                       action_type=enum.ActionType.SYSTEM_CLOSED.value,
                                                       description=enum.EventsForSessionLog.Unknown_Event_Description.value
                                                       )

                    return base.SubTask.close_sub_task_with_task_id(db, task_ids)
                return {"message": "No session found to close"}

            return {"message": "Invalid event key"}

        except Exception as e:
            return {"message": f"An error occurred: {str(e)}"}

    @staticmethod
    def update_session_audit(db: Session, session_id: int, to_update):
        return base.Sessions.update_attributes_in_session_audit(db, session_id, to_update)

    @staticmethod
    def fetch_session(db: Session,
                      parking_lot_id: int,
                      start_date_time: datetime,
                      end_date_time: datetime):

        lot_id = base.ConnectParkinglot.get_connect_parking_lot_id(db, parking_lot_id)
        if not lot_id:
            raise HTTPException(status_code=404, detail="Parking lot is not registered")
        provider_connects = base.ProviderConnect.check_parking_lot_with_provider(db, lot_id.id)
        providers = {}
        for provider in provider_connects:
            provider_by_id = base.Provider.get_by_id(db, provider.provider_id)
            provider_log = {provider_by_id.name: provider_by_id.logo}
            providers.update(provider_log)

        sessions_audit, stats = base.Sessions.get_by_date(db, parking_lot_id,
                                                          start_date_time, end_date_time)
        stats = schema.Stats(**stats)
        session_list = []
        for session_audit in sessions_audit:
            try:
                logs = base.SessionLog.get_session_logs(db, session_audit.id)
                event_list = []
                for log in logs:
                    provider = base.Provider.get_by_id(db, log.provider)
                    if provider is None:
                        events_log = schema.Events(type=log.action_type, description=log.description,
                                                   timestamp=log.created_at)
                    else:
                        paid_price = (log.meta_info.get('price_paid') if log.meta_info else None)
                        events_log = schema.Events(type=log.action_type, description=log.description,
                                                   provider=provider.name,
                                                   timestamp=log.created_at,
                                                   paid_price=paid_price)
                    if events_log is not None:
                        event_list.append(events_log)

                session_list.append(schema.Session(sessionStart=session_audit.session_start_time,
                                                   record_id=session_audit.lpr_record_id,
                                                   title=session_audit.lpr_number.upper(),
                                                   paid_price=session_audit.total_paid_amount,
                                                   isWaitingForPayment=session_audit.is_waiting_for_payment,
                                                   events=event_list))
            except Exception as e:
                logger.critical(f"Logs: Error fetching logs for session id {session_audit.id}")

        return schema.AuditingSchema(stats=stats,
                                     providers=json.dumps(providers),
                                     sessions=session_list)

    @staticmethod
    def fetch_session_v2(db: Session,
                         parking_lot_id: int,
                         start_date_time: datetime,
                         end_date_time: datetime,
                         page_number: int,
                         page_size: int,
                         time_frame):

        lot_id = base.ConnectParkinglot.get_connect_parking_lot_id(db, parking_lot_id)
        if not lot_id:
            raise HTTPException(status_code=404, detail="Parking lot is not registered")
        provider_connects = base.ProviderConnect.check_parking_lot_with_provider(db, lot_id.id)
        providers = {}
        for provider_connect in provider_connects:
            provider_cred = base.ProviderCreds.get_by_id(db, provider_connect.provider_creds_id)
            provider_by_id = base.Provider.get_by_id(db, provider_cred.provider_id)
            provider_log = ""
            if provider_by_id:
                provider_log = {provider_by_id.name: provider_by_id.logo}
            providers.update(provider_log)

        sessions_audit, stats, metadata = base.Sessions.get_by_date_v2(db, parking_lot_id,
                                                                       start_date_time, end_date_time,
                                                                       page_number, page_size)
        stats = schema.Stats(**stats)
        metadata = schema.Metadata(**metadata)

        session_dict = {}
        for session_audit in sessions_audit:
            try:

                logs = base.SessionLog.get_session_logs(db, session_audit.id)
                text_to_show = "waiting for grace period" if session_audit.is_waiting_for_payment else None
                event_list = []
                for log in logs:
                    provider = base.Provider.get_by_id(db, log.provider)
                    if provider is None:
                        events_log = schema.SchemaForNUllProviderINSessionLog(type=log.action_type,
                                                                              description=log.description,
                                                                              timestamp=log.event_at if log.event_at else log.created_at
                                                                              )
                    else:
                        price_paid = log.meta_info.get('price_paid') if log.meta_info else None
                        paid_price = float(price_paid) if price_paid is not None else 0.0
                        formatted_paid_price = "{:.2f}".format(paid_price)
                        if log.action_type.startswith(enum.EventsForSessionLog.VIOLATION_SENT.value):
                            events_log = schema.SessionLogWithoutAmountSchema(type=log.action_type, description=log.description,
                                                       provider=provider.name,
                                                       timestamp=log.event_at if log.event_at else log.created_at
                                                       )
                        else:
                            events_log = schema.Events(type=log.action_type, description=log.description,
                                                       provider=provider.name,
                                                       timestamp=log.event_at if log.event_at else log.created_at,
                                                       amount=formatted_paid_price)
                    if events_log is not None:
                        event_list.append(events_log)
                if session_audit.lpr_number is not None:
                    title = session_audit.lpr_number.upper()
                else:
                    title = f"{session_audit.parking_spot_name}"

                session = schema.Session(sessionStart=session_audit.session_start_time,
                                         session_id=session_audit.id,
                                         spot_id=session_audit.spot_id,
                                         parking_spot_name=f"{session_audit.parking_spot_name}",
                                         record_id=session_audit.lpr_record_id,
                                         title=title,
                                         total_paid_price=session_audit.total_paid_amount,
                                         isWaitingForPayment=session_audit.is_waiting_for_payment,
                                        #  isWaitingForReservation=is_waiting_for_reservation,
                                         text_to_show=text_to_show,
                                         events=event_list)
                session_date = session_audit.session_start_time.date()
                if session_date not in session_dict:
                    session_dict[session_date] = []
                session_dict[session_date].append(session)
            except Exception as e:
                logger.critical(f"Logs: Error fetching logs for session id {session_audit.id} due to {e}")

        sessions_grouped_by_date = [sessions for sessions in session_dict.values()]
        group_by_date = True if time_frame != 'today' and time_frame != 'yesterday' else False
        return schema.AuditingSchemaV2(metadata=metadata,
                                       stats=stats,
                                       group_by_date=group_by_date,
                                       providers=json.dumps(providers),
                                       sessions=sessions_grouped_by_date)

    @staticmethod
    def fetch_session_v3(db: Session,
                         parking_lot_id: int,
                         start_date_time: datetime,
                         end_date_time: datetime,
                         page_number: int,
                         page_size: int,
                         session_type,
                         provider,
                         plate_number_or_spot,
                         time_frame):

        lot_id = base.ConnectParkinglot.get_connect_parking_lot_id(db, parking_lot_id)
        if not lot_id:
            raise HTTPException(status_code=404, detail="Parking lot is not registered")

        providers_info = base.Provider.get_all_providers(db)
        providers_dict = {provider.id: {
            "name": provider.name,
            "logo": provider.logo
        } for provider in providers_info}

        sessions_audit, stats, metadata = base.Sessions.get_by_date_v3(db,
                                                                       parking_lot_id,
                                                                       start_date_time,
                                                                       end_date_time,
                                                                       page_number,
                                                                       page_size,
                                                                       session_type,
                                                                       provider,
                                                                       plate_number_or_spot,
                                                                       )
        stats = schema.Stats(**stats)
        metadata = schema.Metadata(**metadata)

         # Group sessions by date
        daily_sessions = defaultdict(list)
        session_map, providers = {}, {}

        for row in sessions_audit:
            session_id = row.session_id

            if session_id not in session_map:
                session_map[session_id] = {
                    "sessionStart": row.session_start_time.isoformat(),
                    "session_id": session_id,
                    "record_id": row.lpr_record_id,
                    "spot_id": row.spot_id,
                    "parking_spot_name": row.parking_spot_name,
                    "title": row.lpr_number.upper() if row.lpr_number else f"{row.parking_spot_name}",
                    "isWaitingForPayment": row.is_waiting_for_payment,
                    "isWaitingForReservation": False,
                    "text_to_show": "waiting for grace period" if row.is_waiting_for_payment else None,
                    "total_paid_price": row.total_paid_amount,
                    "is_active": row.is_active,
                    "events": []
                }

            event = {
                "type": row.action_type,
                "description": row.description,
                "timestamp": row.log_created_at.isoformat()
            }

            provider_data = providers_dict.get(row.provider)

            if provider_data is not None:
                event["provider"] = provider_data.get("name", "")

                if not row.action_type.startswith(enum.EventsForSessionLog.VIOLATION_SENT.value):
                    price_paid = row.meta_info.get('price_paid') if row.meta_info else None
                    paid_price = float(price_paid) if price_paid is not None else 0.0
                    formatted_paid_price = "{:.2f}".format(paid_price)
                    event["amount"] = formatted_paid_price

                    event_model = schema.Events(**event)
                else:
                    # schema without amount
                    event_model = schema.SessionLogWithoutAmountSchema(**event)

                providers[provider_data["name"]] = provider_data.get("logo")

            # Schema without provider and amount
            else:
                event_model = schema.SchemaForNUllProviderINSessionLog(**event)

            session_map[session_id]["events"].append(event_model)

        # Organizing sessions into daily arrays
        for session in session_map.values():
            session_date = datetime.fromisoformat(session["sessionStart"]).date()
            daily_sessions[session_date].append(session)

        # Convert to the desired output format
        sessions_grouped_by_date = [daily_sessions[date] for date in daily_sessions]

        group_by_date = True if time_frame != 'today' and time_frame != 'yesterday' else False
        return schema.AuditingSchemaV2(metadata=metadata,
                                       stats=stats,
                                       group_by_date=group_by_date,
                                       providers=json.dumps(providers),
                                       sessions=sessions_grouped_by_date)


    @staticmethod
    def check_session_on_car_entry(db: Session, lpr: str, parking_lot: int):
        return base.Sessions.get_session_by_plate(db, lpr, parking_lot)

    @staticmethod
    def check_session_on_spot_occupied(db: Session, spot_id: str, parking_lot: int):
        return base.Sessions.get_session_by_spot(db, spot_id, parking_lot)

    @staticmethod
    def check_session_on_violation(db: Session, parking_lot_id: int, lpr: str, lpr_record_id: int):
        return base.Sessions.get_session_by_lpr_parking_lot_and_lpr_record_id(db, parking_lot_id, lpr, lpr_record_id)

    @staticmethod
    def create_session_logs(db: Session,
                            session_id: int,
                            action_type: str,
                            description: str,
                            meta_info: dict = None,
                            provider: str = None,
                            action: str = None,
                            attributes_dict: dict = None,
                            event_at: Optional[Any] = None
                            ):
        try:
            if action == "UPDATE":
                SessionManager.update_session_audit(db, session_id, attributes_dict)

            session_event = schema.SgSessionLog(session_id=session_id,
                                                action_type=action_type,
                                                description=description,
                                                meta_info=meta_info,
                                                provider=provider,
                                                event_at=event_at)

            session_event = base.SessionLog.insert_session_event(db, session_event)
            return session_event
        except Exception as e:
            logger.critical(f"Logs: Error creating logs for {action_type} for session id {session_id}")

    @staticmethod
    def update_counter(db, session_id: int, action_on: str):
        session_by_id = base.Sessions.get_session_by_id(db, session_id)
        attributes_to_update = {}
        if action_on == "paid":
            attributes_to_update.update({"not_paid_counter": 0})

        if action_on == "not paid":
            attributes_to_update.update({"not_paid_counter": session_by_id.not_paid_counter + 1})

        base.Sessions.update_attributes_in_session_audit(db, session_by_id.id, attributes_to_update)

    @staticmethod
    def check_session_to_map_lpr_to_spot(db: Session, lpr: str, lpr_record_id: int):
        return base.Sessions.get_by_lpr_record_id(db, lpr, lpr_record_id)