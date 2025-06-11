from sqlalchemy import (Column,
                        String,
                        Integer,
                        JSON,
                        ForeignKey, func, desc, or_, DateTime
                        )
from sqlalchemy.orm import Session
from app.models.base import Base
from app.schema import SgSessionLog


class SessionLog(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('sessions.id'), name="fk_sessions", nullable=False)
    action_type = Column(String, nullable=False)
    description = Column(String, nullable=False)
    provider = Column(Integer, nullable=True)
    meta_info = Column(JSON, nullable=True)
    event_at = Column(DateTime, nullable=True)

    @classmethod
    def insert_session_event(cls, db: Session, sg_session: SgSessionLog):

        last_session_log = db.query(cls).filter(cls.session_id == sg_session.session_id).order_by(
            desc(cls.created_at)).first()

        from app.utils import enum
        if (last_session_log and sg_session.action_type in enum.EventsForSessionLog.SKIP_INSERT_IF_LAST_LOG_MATCHES.value
                and sg_session.action_type == last_session_log.action_type):
            return last_session_log

        elif sg_session.action_type == enum.EventsForSessionLog.not_paid.value:
            existing_record = db.query(cls).filter(
                            cls.session_id == sg_session.session_id,
                            cls.action_type == sg_session.action_type
                        ).first()

            if existing_record:
                if last_session_log and (
                            (
                                last_session_log.action_type.startswith(enum.EventsForSessionLog.paid.value) 
                                or last_session_log.action_type == enum.EventsForSessionLog.PAYMENT_ALERT_CLOSED.value or last_session_log.action_type == enum.EventsForSessionLog.OVERSTAY_ALERT_CLOSED.value
                            )
                        ):
                    pass
                else:
                    return last_session_log

        # Create new records for other action types, including "Paid"
        sg_session = cls(**sg_session.model_dump())
        db.add(sg_session)
        db.commit()
        db.refresh(sg_session)

        return sg_session

    @classmethod
    def get_session_logs(cls, db: Session, session_id: int):
        session_logs = db.query(cls).filter(cls.session_id == session_id).order_by(cls.id).all()
        # session_logs.sort(key=lambda log: (log.created_at, log.id))
        return session_logs

    @classmethod
    def check_if_entry_or_exit_associate_with_session(cls, db, session_id: int, action_type: str):

        exists = db.query(func.count(cls.id)).filter(
            cls.session_id == session_id,
            cls.action_type.ilike(f'%{action_type}%')
        ).scalar() > 0
        return exists

    @classmethod
    def check_last_session_by_action_type(cls, db: Session, session_id: int, search_values: list):
        return db.query(cls).filter(
            cls.session_id == session_id,
            or_(
                cls.action_type.ilike(f'%{value}%') for value in search_values
            )
        ).order_by(desc(cls.created_at)).first()
