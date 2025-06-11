import logging
from datetime import datetime, timezone
from typing import List, Union

from sqlalchemy import (Column,
                        String,
                        Integer,
                        ForeignKey,
                        TIMESTAMP,
                        ARRAY,
                        JSON,
                        or_,
                        case, update, func, cast,
                        select, asc
                        )
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session
from app import schema
from app.models.base import Base
from app.models.feature_url_path import FeatureUrlPath
from app.models.feature import Feature
from app.config import settings
from app.utils import enum
from app.models import base
from app.models.context_session import get_db_session

logger = logging.getLogger(__name__)


class Task(Base):
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    status = Column(String, nullable=False, default=enum.TaskStatus.PENDING.value)
    event_type = Column(String, nullable=False)
    parking_lot_id = Column(Integer, nullable=False)
    parking_spot_id = Column(String, nullable=True)
    parking_spot_name = Column(String, nullable=True)
    next_at = Column(TIMESTAMP, nullable=True)
    plate_number = Column(String, nullable=True)
    state = Column(String, nullable=True)
    feature_text_key = Column(String, nullable=False)
    sgadmin_alerts_ids = Column(ARRAY(Integer), nullable=True)
    sg_event_response = Column(JSON, nullable=True)
    session_id = Column(Integer, nullable=True)
    provider_type = Column(Integer, ForeignKey("provider_types.id"), name="fk_provider_type", nullable=False)
    alert_status = Column(String, nullable=True)

    @classmethod
    def create_task(cls, db: Session, task_create_schema: schema.TaskCreateSchema):
        """Creates a new task."""
        task = cls(**task_create_schema.model_dump())
        db.add(task)
        db.commit()
        db.refresh(task)

        if task.event_type == enum.Event.lpr_exit.value:
            violation_tasks = cls.check_violation_on_session(db, task.session_id, task.feature_text_key)
            from app.utils.common import execute_violation_before_exit
            [execute_violation_before_exit(db, vt) for vt in violation_tasks]

            cls.close_task_with_plate_number(db, task.parking_lot_id, task.plate_number)
            base.Violation.update_session(db, task.plate_number,
                                          "CLOSE")
            attribute_to_update = {"is_active": False,
                                   "is_waiting_for_payment": False}
            base.Sessions.update_attributes_in_session_audit(db, task.session_id, attribute_to_update)

        if task.event_type == enum.Event.available.value:
            cls.close_task_with_spot_id(db, task.parking_lot_id, task.parking_spot_id, task.session_id)
            base.Violation.update_session_by_spot_id(db, task.parking_spot_id, task.session_id,
                                                     "CLOSE")

            attribute_to_update = {"is_active": False,
                                   "is_waiting_for_payment": False}
            base.Sessions.update_attributes_in_session_audit(db, task.session_id, attribute_to_update)

        return task

    @classmethod
    def get_task_by_id(cls, db: Session, task_id: int):
        get_task = db.query(cls).get(task_id)
        return get_task

    @classmethod
    def get_task_by_session_id(cls, db: Session, session_id: int):
        task = db.query(cls).filter(cls.session_id == session_id).first()
        return task

    @classmethod
    def get_task_to_execute(cls, db: Session):

        # event timestamp is not used in task, so for that reason we are picking up by id
        tasks = (
            db.query(Task)
            .filter(
                Task.status == enum.TaskStatus.PENDING.value,
                Task.next_at < datetime.now(timezone.utc)
            )
            .order_by(Task.id)
            .limit(settings.TASK_PICKING_LIMIT)
            .with_for_update(skip_locked=True)
            .all()
        )

        if not tasks:
            return []

        task_ids = [task.id for task in tasks]

        db.query(Task).filter(Task.id.in_(task_ids)).update(
            {Task.status: enum.TaskStatus.IN_PROGRESS.value},
            synchronize_session=False
        )
        db.commit()
        return Task.get_in_progress_task(db)

    @classmethod
    def get_in_progress_task(cls, db: Session):
        query = db.query(Task).filter(
            Task.status == enum.TaskStatus.IN_PROGRESS.value,
            Task.next_at < datetime.utcnow()
        ).order_by(
            Task.session_id,  # Group by session ID
            case((Task.feature_text_key == enum.Feature.NOTIFY_SG_ADMIN.value, 1),
                 (Task.feature_text_key == enum.Feature.RESERVATION_CHECK_LPR.value, 2),
                 (Task.feature_text_key == enum.Feature.PAYMENT_CHECK_LPR.value, 3),
                 else_=4), asc(base.Task.id)
        ).limit(settings.TASK_PICKING_LIMIT)
        return query

    @classmethod
    def get_feature_url(cls, db: Session, task_id: int):
        task = db.query(Task).get(task_id)
        provider_feature = db.query(Feature).filter_by(text_key=task.feature_text_key).first()
        if provider_feature:
            return db.query(FeatureUrlPath).filter_by(feature_id=provider_feature.id).first()
        return None

    @classmethod
    def close_task_for_parking_lot_and_spot(cls, db: Session, spot_id: int,
                                            lot_id: int):
        db.query(Task).filter(Task.parking_spot_id == spot_id,
                              Task.parking_lot_id == lot_id,
                              or_(Task.status == "PENDING", Task.status == "IN_PROGRESS")).update(
            {Task.status: case(
                (Task.event_type == enum.EventTypes.SPOT_FREE.value, enum.TaskStatus.COMPLETED.value),
                else_=enum.TaskStatus.CLOSED.value)},
            synchronize_session=False
        )

        db.commit()

    @classmethod
    def close_task_with_plate_number(cls, db: Session, lot_id: int,
                                     plate_number: str):
        db.query(Task).filter(Task.plate_number == plate_number,
                              Task.parking_lot_id == lot_id,
                              Task.event_type != enum.EventTypes.VIOLATION_INACTIVE.value,
                              or_(Task.status == "PENDING", Task.status == "IN_PROGRESS")).update(
            {Task.status: case(
                (Task.event_type == 'car.exit', enum.TaskStatus.PENDING.value),
                else_=enum.TaskStatus.CLOSED.value)},
            synchronize_session=False
        )

    @classmethod
    def close_task_with_plate_number_and_session_id(cls, db: Session, lot_id: int,
                                     plate_number: str, session_id: int):
        db.query(Task).filter(Task.plate_number == plate_number,
                              Task.parking_lot_id == lot_id,
                              Task.session_id == session_id,
                              Task.event_type != enum.EventTypes.VIOLATION_INACTIVE.value,
                              or_(Task.status == "PENDING", Task.status == "IN_PROGRESS")).update(
            {Task.status: case(
                (Task.event_type == 'car.exit', enum.TaskStatus.PENDING.value),
                else_=enum.TaskStatus.CLOSED.value)},
            synchronize_session=False
        )

    @classmethod
    def close_task_with_spot_id(cls, db: Session, lot_id: int,
                                spot_id: str, session_id: int):
        db.query(Task).filter(Task.parking_spot_id == spot_id,
                              Task.parking_lot_id == lot_id,
                              Task.session_id == session_id,
                              Task.event_type != enum.EventTypes.VIOLATION_INACTIVE.value,
                              or_(Task.status == "PENDING", Task.status == "IN_PROGRESS")).update(
            {Task.status: case(
                (Task.event_type == enum.Event.available.value, enum.TaskStatus.PENDING.value),
                else_=enum.TaskStatus.CLOSED.value)},
            synchronize_session=False
        )

    @classmethod
    def close_task(cls, db: Session, task):
        if task.event_type in ('lpr_exit', 'car.exit'):
            db.query(cls).filter(
                    cls.session_id == task.session_id,
                    cls.feature_text_key != enum.Feature.ENFORCEMENT_NOTIFICATION.value
                ).update({cls.status: enum.TaskStatus.CLOSED.value})
        task.status = enum.TaskStatus.CLOSED.value
        db.commit()

    @classmethod
    def get_task_car_exit(cls, db: Session, plate_number, parking_lot_id):

        task = db.query(cls).order_by(cls.created_at).filter(cls.plate_number == plate_number,
                                                             cls.parking_lot_id == parking_lot_id,
                                                             or_(cls.status == enum.TaskStatus.PENDING.value,
                                                                 cls.status == enum.TaskStatus.IN_PROGRESS.value)).first()
        return task

    @classmethod
    def get_task_spot_free(cls, db: Session, parking_spot_id, parking_lot_id):

        task = db.query(cls).order_by(cls.created_at).filter(cls.parking_spot_id == parking_spot_id,
                                                             cls.parking_lot_id == parking_lot_id,
                                                             or_(cls.status == enum.TaskStatus.PENDING.value,
                                                                 cls.status == enum.TaskStatus.IN_PROGRESS.value)).first()
        return task

    @classmethod
    def close_task_for_missed_car_exit_event(cls, db: Session, parking_lot_id: int, plate_number: str):
        db.query(cls).filter(cls.parking_lot_id == parking_lot_id,
                             cls.plate_number == plate_number,
                             cls.event_type == enum.EventTypes.CAR_ENTRY.value,
                             cls.status.in_([enum.TaskStatus.PENDING.value, enum.TaskStatus.IN_PROGRESS.value])
                             ).update({cls.status: enum.TaskStatus.CLOSED.value})

    @classmethod
    def check_car_exists(cls, db: Session, parking_lot_id: int, plate_number: str):
        return db.query(cls).filter(cls.parking_lot_id == parking_lot_id,
                                    cls.plate_number == plate_number).first()

    @classmethod
    def close_task_with_session_id(cls, db: Session, session_id: int) -> List[int]:
        update_stmt = update(cls).where(
            cls.session_id == session_id,
            # cls.event_type == enum.EventTypes.SPOT_OCCUPIED.value,
            cls.status.in_([enum.TaskStatus.PENDING.value, enum.TaskStatus.IN_PROGRESS.value])
        ).values(
            status=enum.TaskStatus.CLOSED.value
        ).returning(cls.id)

        result = db.execute(update_stmt)
        task_ids = [row.id for row in result]
        db.commit()
        logger.info(f" closed task IDs: {task_ids}")
        return task_ids

    @classmethod
    def session_contains_both_rp(cls, db, session_id, feature_type):

        filter_by_feature = {
            'payment': [enum.Feature.PAYMENT_CHECK_LPR.value, enum.Feature.PAYMENT_CHECK_SPOT.value],
            'reservation': [enum.Feature.RESERVATION_CHECK_LPR.value],
        }

        task_exists = db.query(cls).filter(
            cls.session_id == session_id,
            cls.feature_text_key.in_(filter_by_feature[feature_type])
        ).first()

        return task_exists is not None

    @classmethod
    def check_session_task_existence(cls, db, session_id) -> Union[tuple[bool, bool]]:

        # Check if the session has a reservation
        has_reservation = db.query(cls).filter(
            cls.session_id == session_id,
            cls.feature_text_key == enum.Feature.RESERVATION_CHECK_LPR.value
        ).first() is not None

        # Check if the session has a payment
        has_payment = db.query(cls).filter(
            cls.session_id == session_id,
            cls.feature_text_key.in_([enum.Feature.PAYMENT_CHECK_LPR.value, enum.Feature.PAYMENT_CHECK_SPOT.value])
        ).first() is not None

        return has_reservation, has_payment

    @classmethod
    def validate_secondary_lprs(cls, plate_numbers, parking_lot_id):
        db = get_db_session()

        return db.query(cls).filter(
            cls.status != 'CLOSED',
            cls.plate_number.in_(plate_numbers),
            cls.parking_lot_id == parking_lot_id
        ).first() is not None

    @classmethod
    def update_task(cls, db, task, alert_ids: [int]):

        try:
            task.sgadmin_alerts_ids = alert_ids  # Directly modify the instance's attribute

            db.commit()  # Commit the transaction
            return task  # Optionally return the updated task
        except Exception as e:
            db.rollback()  # Rollback the session in case of error
            print("Error occurred while updating task:", e)
            return None  # Or handle it as appropriate

    @classmethod
    def check_violation_on_session(cls, db, session_id, feature_type):

        filter_by_status = [enum.TaskStatus.PENDING.value, enum.TaskStatus.IN_PROGRESS.value]

        violation = db.query(cls).filter(
            cls.session_id == session_id,
            or_(
                cls.feature_text_key == enum.Feature.NOTIFY_SG_ADMIN.value,
                cls.feature_text_key == enum.Feature.ENFORCEMENT_CITATION.value,
            ),
            cls.status.in_(filter_by_status)
        ).all()

        return violation

    @classmethod
    def get_pending_payment_violation(cls, db, provider_type_id: int, session_id: int):
        return db.query(base.Task).filter(
                base.Task.provider_type == provider_type_id,
                base.Task.event_type == enum.Event.payment_violation.value,
                base.Task.session_id == session_id,
                or_(base.Task.alert_status != enum.ViolationStatus.CLOSED.value, base.Task.alert_status.is_(None))
            ).first()

    @classmethod
    def get_pending_overstay_violation(cls, db, provider_type_id: int, session_id: int):
        return db.query(base.Task).filter(
                base.Task.provider_type == provider_type_id,
                base.Task.event_type == enum.Event.overstay_violation.value,
                base.Task.session_id == session_id,
                or_(base.Task.alert_status != enum.ViolationStatus.CLOSED.value, base.Task.alert_status.is_(None))
            ).first()

    @classmethod
    def update_alert_status(cls, db, opened_violation_task, status):
        opened_violation_task.alert_status = status
        db.commit()

    @classmethod
    def update_task_by_session_id(cls, db, session_id: int, spot_id: int, parking_spot_name: str):

        update_spot_id = (db.query(cls).filter(
            cls.session_id == session_id,
            cls.status.in_([enum.TaskStatus.PENDING.value, enum.TaskStatus.IN_PROGRESS.value])
        )
        .update(
            {
                cls.parking_spot_id: spot_id,
                cls.parking_spot_name: parking_spot_name
            },
            synchronize_session=False
        ))
        db.commit()  # Commit the changes to the database
        if update_spot_id:

            return update_spot_id
        return None

    @classmethod
    def append_lr_image_to_sg_event_response(cls, db, session_id, key, value):

        stmt = (
            update(cls)
            .where(cls.session_id == session_id)  # Condition to update all records where session_id matches
            .values(
                sg_event_response=cast(  # Cast the updated JSONB back to JSON
                    func.jsonb_set(
                        func.coalesce(
                            cast(cls.sg_event_response, JSONB),  # Cast to JSONB first
                            func.cast('{}', JSONB)  # If NULL, initialize as an empty JSONB object
                        ),
                        f'{{{key}}}',  # Key to be updated
                        f'"{value}"',  # Value to be assigned
                        True  # Create key if it doesn't exist
                    ),
                    JSON  # Cast the result back to JSON
                )
            )
        )

        # Execute the statement and commit the changes
        db.execute(stmt)
        db.commit()

    @classmethod
    def fetch_spot_details_by_session_id(cls, db, session_id: int):

        spot_detail = db.query(cls).filter(cls.session_id == session_id,  cls.parking_spot_id.isnot(None)).first()
        if spot_detail:
            return spot_detail
        return None

    @classmethod
    def close_enforcement_task_sub_task(
        cls,
        db,
        session_id: int,
        event_type: str,
        feature_text_type: str
    ):
        enforcement_task = db.query(cls).filter(
            cls.event_type == event_type,
            cls.session_id == session_id,
            cls.feature_text_key == feature_text_type,
            cls.status != enum.TaskStatus.CLOSED.value
        ).first()

        if enforcement_task:
            enforcement_task.status = enum.TaskStatus.CLOSED.value
            base.SubTask.close_sub_task_with_task_id(
                db,
                task_ids=[enforcement_task.id]
            )

            db.commit()

        return enforcement_task

    @classmethod
    def get_column_value_by_id(cls, db, task_id: int, column_name: str):
        """Fetches a dynamic column value of a user by their ID"""
        # Dynamically get the column by its name
        column = getattr(cls, column_name, None)
        stmt = select(column).where(cls.id == task_id)
        return db.execute(stmt).scalar()
