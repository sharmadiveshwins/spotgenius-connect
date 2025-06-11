from sqlalchemy import (Column,
                        String,
                        Integer,
                        TIMESTAMP,
                        ForeignKey,
                        JSON
                        )
from app.models import base
from sqlalchemy.sql import func
from sqlalchemy.orm import Session
from app import schema
from app.utils import enum
from sqlalchemy import select


class Violation(base.Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    status = Column(String, default=enum.ViolationStatus.OPEN.value)
    description = Column(String)
    timestamp = Column(TIMESTAMP, nullable=True)
    task_id = Column(Integer, ForeignKey("task.id"), name="fk_task", nullable=False)
    violation_type = Column(String, nullable=True)
    amount_due = Column(Integer, nullable=False, default=0)
    parking_spot_id = Column(String, nullable=True)
    plate_number = Column(String, nullable=True)
    parking_lot_id = Column(Integer, nullable=True)
    session = Column(String, nullable=True, default="OPEN")
    session_id = Column(Integer, nullable=True)
    citation_id = Column(String, nullable=True)
    citation_inactivation_id = Column(String, nullable=True)
    meta_data = Column(JSON, nullable=True)
    violation_event = Column(JSON, nullable=True)

    @classmethod
    def create_violation(cls, db: Session, violation_details: schema.Violation):
        """Creates a new violation."""

        violation = Violation(**violation_details.model_dump())
        db.add(violation)
        db.commit()
        db.refresh(violation)
        return violation

    @classmethod
    def update_violation(cls, db: Session, plate_number: str, parking_spot_id: str, feature_text_key: str):
        update_violation = None

        if feature_text_key == enum.Feature.PAYMENT_CHECK_SPOT.value:
            update_violation = db.query(cls).filter(cls.plate_number == plate_number, cls.status == "OPEN").first()
        elif feature_text_key == enum.Feature.PAYMENT_CHECK_LPR.value:
            update_violation = db.query(cls).filter(cls.parking_spot_id == parking_spot_id, cls.status == "OPEN").first()

        if update_violation is not None:
            update_violation.amount_due = update_violation.amount_due + 10
            db.add(update_violation)
            db.commit()
            db.refresh(update_violation)
            return update_violation
        return None

    @classmethod
    def update_status(cls, db: Session, violation_id: int, status: str):
        update_status = db.query(cls).get(violation_id)
        update_status.status = status
        db.add(update_status)
        db.commit()
        db.refresh(update_status)
        return update_status

    @classmethod
    def update_session(cls, db: Session, plate_number: int, session_status: str):
        update_status = db.query(cls).filter(cls.plate_number == plate_number).first()
        if update_status:
            update_status.session = session_status
            db.add(update_status)
            db.commit()
            db.refresh(update_status)
        return update_status

    @classmethod
    def update_session_by_spot_id(cls, db: Session, spot_id: int, session_id: int, session_status: str):
        update_status = db.query(cls).filter(cls.parking_spot_id == spot_id,
                                             cls.session_id == session_id).first()
        if update_status:
            update_status.session = session_status
            db.add(update_status)
            db.commit()
            db.refresh(update_status)
        return update_status

    @classmethod
    def update(cls, db: Session, session_id: int, to_update):
        session = db.query(cls).filter(cls.session_id == session_id).first()
        if session:
            try:
                for key, value in to_update.items():
                    if hasattr(session, key):
                        setattr(session, key, value)
                db.commit()
                return session
            except Exception as e:
                db.rollback()
                print("Error occurred during update:", e)
                return None
        return None

    @classmethod
    def get_violation_by_session_id(cls, db: Session, session_id: int, violation_type: str):
        violation = db.query(cls).filter(cls.session_id == session_id,
                                                 cls.violation_type == violation_type,
                                                  cls.status == "OPEN").first()
        if violation:
            return violation


    @classmethod
    def get_all_violation_associate_with_session(cls, db, session_id):
        violation = db.query(cls).filter(cls.session_id == session_id, cls.citation_inactivation_id.is_(None)).all()
        if violation:
            return violation

    @classmethod
    def update_by_session_and_task(cls, db: Session, session_id: int, task_id: int, to_update):
        session = db.query(cls).filter(cls.session_id == session_id, cls.task_id == task_id).first()
        if session:
            try:
                for key, value in to_update.items():
                    if hasattr(session, key):
                        setattr(session, key, value)
                db.commit()
                return session
            except Exception as e:
                db.rollback()
                print("Error occurred during update:", e)
                return None
        return None

    @classmethod
    def update_by_violation_and_session_id(cls, db: Session, session_id: int, violation_id: int, to_update):

        session = db.query(cls).filter(cls.session_id == session_id, cls.id == violation_id).first()
        if session:
            try:
                for key, value in to_update.items():
                    if hasattr(session, key):
                        setattr(session, key, value)
                db.commit()
                return session
            except Exception as e:
                db.rollback()
                print("Error occurred during update:", e)
                return None
        return None

    @classmethod
    def check_for_inactivation_feature(cls, db: Session, parking_lot_id: int, session_id: int):
            subquery_parkinglot = select(base.ConnectParkinglot.id).where(base.ConnectParkinglot.parking_lot_id == parking_lot_id)
            subquery_provider = select(base.ProviderConnect.id).where(
                base.ProviderConnect.connect_id.in_(subquery_parkinglot))
            subquery_feature = select(base.Feature.id).where(base.Feature.text_key == 'enforcement.inactivate')
            #
            query = select(base.ParkinglotProviderFeature).where(
                base.ParkinglotProviderFeature.provider_connect_id.in_(subquery_provider),
                base.ParkinglotProviderFeature.feature_id.in_(subquery_feature))

            if db.scalars(query).first():
                subq = select(base.Violation).where(base.Violation.session_id.in_([session_id]))
                if db.scalars(subq).first():
                    return True

    @classmethod
    def get_violation_by_task_and_session_id(cls, db: Session,task_id, session_id):

        session = db.query(cls).filter(cls.session_id == session_id, cls.task_id == task_id).first()

        if session:
            return session
        return None