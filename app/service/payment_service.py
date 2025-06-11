import json
import logging
from datetime import datetime, timezone
from fastapi import Response
from typing import List, Optional

from app import schema
from app.models.connect_parkinglot import ConnectParkinglot
from app.models.violation import Violation
from app.models.violation_configuration import ViolationConfiguration
from app.models.push_payment import PushPayment
from app.schema.citation_schema import CreateCitationSchema
from app.service.event_service import EventService
from app.service.alert_service import AlertSgadmin
from app.utils import enum
from app.utils.common import DateTimeUtils, build_task_from_event, fetch_violation_amount, get_violation_id
from app.utils.email import send_email
from app.models import base
from app.schema import session_schema
from app.service import session_manager
from app.utils.common import car_identification_log
from app.utils.violation_rule import ViolationRule

logger = logging.getLogger(__name__)


class PaymentService:

    @staticmethod
    def paid(db, task, sub_task, response_schema, timestamp):
        # alert_id_list = task.sgadmin_alerts_ids
        provider_type = db.query(base.ProviderTypes).filter(base.ProviderTypes.text_key == enum.ProviderTypes.PROVIDER_VIOLATION.value).first()

        provider_creds_by_id = base.ProviderCreds.get_by_id(db, sub_task.provider_creds_id)
        provider = base.Provider.get_by_id(db, provider_creds_by_id.provider_id)
        attributes_to_update = {"is_waiting_for_payment": False}
        if response_schema.action_type in enum.EventsForSessionLog.DURATION_ON_LOG.value:
            time_paid_for = response_schema.action_type + ":" + str(
            DateTimeUtils.calculate_time_difference(response_schema.expiry_date, str(datetime.now(timezone.utc))))
        else:
            time_paid_for = response_schema.action_type
        sessions = base.Sessions.get_session_by_id(db, task.session_id)
        if sessions:
            if response_schema.price_paid is not None:
                total_paid_amount = sessions.total_paid_amount if sessions.total_paid_amount is not None else 0.0
                attributes_to_update.update(
                    {"total_paid_amount": total_paid_amount + float(response_schema.price_paid)})
        session_manager.SessionManager.create_session_logs(db=db,
                                                           attributes_dict=attributes_to_update,
                                                           session_id=task.session_id,
                                                           action_type=time_paid_for,
                                                           description=time_paid_for,
                                                           meta_info=response_schema.__dict__,
                                                           action="UPDATE",
                                                           provider=provider.id if provider is not None else None)

        # close payment violation
        reason = enum.AlertInactiveReason.PAYMENT_FOUND.value
        ViolationRule.close_payment_violation(db, task, reason)
        # TODO ensure that task is getting created for inactivation
        check_for_inactivation_feature = base.Violation.check_for_inactivation_feature(db,
                                                                                       parking_lot_id=task.parking_lot_id,
                                                                                       session_id=task.session_id)
        if check_for_inactivation_feature:
            EventService.execute_event_for_inactivation_task(db, task)

        # TODO
        # Need to remove below code once end-to-end gets validate
        task_schema = PaymentService.new_task_schema(
            parking_lot_id=task.parking_lot_id,
            parking_spot_id=task.parking_spot_id,
            event_type=task.event_type,
            provider_type=task.provider_type,
            feature_text_key=task.feature_text_key,
            next_at=timestamp,
            plate_number=task.plate_number,
            sgadmin_alerts_ids=task.sgadmin_alerts_ids,
            sg_event_response=task.sg_event_response,
            session_id=task.session_id
        )

        return task_schema

    @staticmethod
    def not_paid(task, db, action_type: Optional[str], violation_type, violation_flag=False):
        # car_identification for dynamically showing logs for LPR or Spot based
        car_identification = car_identification_log(task)

        logger.warning(f"Task: {task.id} / {car_identification} - No payment was found from any provider")
        parking_lot = ConnectParkinglot.get(db, task.parking_lot_id)

        sgadmin_alerts = None
        violation_configuration = ViolationConfiguration.get_violation_by_lot_id(db, parking_lot.id)

        logger.info(f"fetching violation amount for alert id {get_violation_id(violation_type)}")
        violation_meta_data = fetch_violation_amount(db, task.parking_lot_id, get_violation_id(violation_type))

        if violation_configuration:
            get_violation = Violation.get_violation_by_session_id(db, task.session_id, violation_type)
            if violation_configuration.pricing_type == 'VARIABLE':
                violation_details = PaymentService.violation_schema_mapping(task, violation_type, violation_meta_data)

                if get_violation:
                    updated_violation = Violation.update_violation(db, task.plate_number, task.parking_spot_id,
                                                                   task.feature_text_key)

                    if updated_violation:
                        logger.error(
                            f"Task: {task.id} / {car_identification} - Violation has been updated for with Id: {updated_violation.id}")
                else:

                    violation = Violation.create_violation(db, violation_details)
                    logger.error(
                        f"Task: {task.id} / {car_identification} - Violation has been created with Id: {violation.id}")

            if violation_configuration.pricing_type == 'FIXED':

                if Violation.get_violation_by_session_id(db, task.session_id, violation_type) is None and violation_flag:
                    new_task = PaymentService.execute_event_to_create_task_on_violation(db, task, violation_type)
                    violation_details = PaymentService.violation_schema_mapping(new_task, violation_type, violation_meta_data)
                    violation = Violation.create_violation(db, violation_details)
                    logger.error(
                        f"Task: {new_task.id} / {car_identification} - Violation has been created with Id: {violation.id}")


    @staticmethod
    def check_payment_service(request, db):

        push_payments = PushPayment.fetch_arrive_payments(db, request.location_id)
        if push_payments:
            return push_payments
        response = Response(status_code=404)
        return response

    @staticmethod
    def check_payment_service_by_spot(request_body, db):
        parking_lot = ConnectParkinglot.get_connect_parking_lot_id(db,
                                                                   request_body.parking_lot_id
                                                                   )
        push_payment = PushPayment.check_payment_by_spot(db,
                                                         request_body.spot_id,
                                                         request_body.provider_id,
                                                         request_body.location_id,
                                                         parking_lot.is_in_out_policy
                                                         )
        if push_payment:
            PushPayment.update_payment_status(db, push_payment.id)
            return push_payment
        response = Response(status_code=404)
        return response

    @staticmethod
    def new_task_schema(parking_lot_id: int,
                        parking_spot_id: str,
                        session_id: str,
                        event_type: str,
                        provider_type: int,
                        feature_text_key: str,
                        next_at: datetime,
                        plate_number: str,
                        sgadmin_alerts_ids: Optional[List[int]],
                        sg_event_response: Optional[dict]
                        ):

        new_event_schema = schema.TaskCreateSchema(
            parking_lot_id=parking_lot_id,
            parking_spot_id=parking_spot_id,
            session_id=session_id,
            event_type=event_type,
            provider_type=provider_type,
            feature_text_key=feature_text_key,
            next_at=next_at,
            plate_number=plate_number,
            sgadmin_alerts_ids=sgadmin_alerts_ids,
            sg_event_response=sg_event_response
        )
        return new_event_schema

    @staticmethod
    def violation_schema_mapping(task, violation_type, meta_data) -> schema.Violation:

        violation_mapping = {
            enum.EventTypes.OVERSTAY_VIOLATION.value: {
                'name': 'Overstay Violation',
                'description': 'Vehicle overstayed'
            },
            enum.EventTypes.PAYMENT_VIOLATION.value: {
                'name': 'Payment Violation',
                'description': 'Payment not found'
            }
        }

        violation_details = violation_mapping.get(violation_type, violation_mapping[enum.EventTypes.PAYMENT_VIOLATION.value])

        mapped_schema_violation = schema.Violation(
            name=violation_details['name'],
            status=enum.ViolationStatus.OPEN.value,
            session=enum.ViolationStatus.OPEN.value,
            description=violation_details['description'],
            task_id=task.id,
            amount_due=meta_data.get("amount", 0),
            plate_number=task.plate_number,
            parking_spot_id=task.parking_spot_id,
            parking_lot_id=task.parking_lot_id,
            violation_type=violation_type,
            session_id=task.session_id,
            meta_data=meta_data,
            timestamp=datetime.utcnow()
        )

        return mapped_schema_violation

    @staticmethod
    def execute_event_to_create_task_on_violation(db, task, task_type):

        session_by_id = base.Sessions.get_session_by_id(db, task.session_id)
        str_to_dict = json.loads(session_by_id.entry_event)
        anpr_event_schema = schema.SgAnprEventSchema(**str_to_dict)
        attributes = {
            "event_key": task_type,
            "session_id": session_by_id.id,
            "parking_spot_name": session_by_id.parking_spot_name,
            "parking_spot_id": session_by_id.spot_id
        }
        for attr, value in attributes.items():
            setattr(anpr_event_schema, attr, value)
        event = EventService.execute_event(events=[anpr_event_schema], db=db, timestamp=datetime.utcnow())
        if event is not None:
            task = base.Task.get_task_by_id(db, event.get("task_id"))
            return task


