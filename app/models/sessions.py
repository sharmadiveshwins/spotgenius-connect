from datetime import datetime
from email.policy import default
from math import ceil
from typing import cast

from sqlalchemy import (Column,
                        String,
                        Integer,
                        DateTime,
                        TIMESTAMP, JSON, Boolean, desc, exists, or_, Float, ARRAY, select
                        )
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base
from app.models import base
from sqlalchemy.orm import Session, aliased
from app.schema import SgSessionAudit
from sqlalchemy import func, and_, case
from sqlalchemy.dialects import postgresql
from app.utils import enum


class Sessions(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_event = Column(JSON, nullable=False)
    exit_event = Column(JSON, nullable=True)
    lpr_number = Column(String, nullable=True)
    spot_id = Column(String, nullable=True)
    parking_spot_name = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    parking_lot_id = Column(Integer, nullable=False)
    session_start_time = Column(TIMESTAMP, nullable=False)
    session_end_time = Column(TIMESTAMP, nullable=True)
    session_total_time = Column(Integer, nullable=True)
    is_waiting_for_payment = Column(Boolean, nullable=True)
    not_paid_counter = Column(Integer, nullable=False, default=0)
    lpr_record_id = Column(Integer, nullable=True)
    total_paid_amount = Column(Float, nullable=True)
    has_nph_task = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime, nullable=True)
    is_lpr_to_spot = Column(Boolean, nullable=True)

    @classmethod
    def insert_sg_admin_events(cls, db: Session, sg_event: SgSessionAudit):

        session_audit = cls(**sg_event.model_dump())
        db.add(session_audit)
        db.commit()
        db.refresh(session_audit)
        return session_audit

    @classmethod
    def get_session_by_id(cls, db: Session, session_id: int):
        session_by_id = db.query(cls).get(session_id)
        return session_by_id

    @classmethod
    def get_session_by_plate(cls, db: Session, lpr: str, parking_lot: int):
        session = db.query(Sessions).filter(Sessions.lpr_number == lpr,
                                            Sessions.parking_lot_id == parking_lot,
                                            Sessions.is_active == True) \
            .filter(func.jsonb_typeof(Sessions.entry_event.cast(JSONB)) != 'null') \
            .order_by(desc(Sessions.id)) \
            .first()
        if session:
            return session
        return None

    @classmethod
    def get_by_lpr_record_id(cls, db: Session, lpr: str, lpr_record_id: int):

        session = db.query(cls).filter(
            (cls.lpr_number == lpr) & (cls.lpr_record_id == lpr_record_id)
        ).order_by(desc(cls.id)).first()
        if session:
            return session
        return None


    @classmethod
    def get_session_by_spot(cls, db: Session, spot_id: str, parking_lot: int):
        session = (db.query(cls).filter( cls.spot_id == spot_id,
                                         cls.parking_lot_id == parking_lot,
                                         cls.is_active == True)
                   .filter(func.jsonb_typeof(Sessions.entry_event.cast(JSONB)) != 'null')
                   .order_by(desc(cls.id)).first())
        if session:
            return session
        return None

    @classmethod
    def update_attributes_in_session_audit(cls, db: Session, session_id: int, to_update):
        session = db.query(cls).get(session_id)

        if session:
            for key, value in to_update.items():
                if hasattr(session, key):
                    setattr(session, key, value)
                    db.commit()
            return session
        return None

    @classmethod
    def get_by_date(cls, db: Session, parking_lot_id: int, from_date: datetime, to_date: datetime):

        subquery = exists().where(base.SessionLog.session_id == cls.id)

        results = db.query(cls).filter(cls.parking_lot_id == parking_lot_id,
                                       cls.created_at.between(from_date, to_date),
                                       func.json_typeof(cls.entry_event) != 'null',
                                       subquery).order_by(desc(cls.created_at)).all()
        violation_counts = db.query(func.count(base.Violation.session_id),
                                    base.Violation.session_id).group_by(
            base.Violation.session_id).all()
        violation_dict = {session_id: count for count, session_id in violation_counts}
        compliant_count = db.query(func.count(cls.id)).filter(
            cls.parking_lot_id == parking_lot_id,  # Added parking lot condition
            ~exists().where(base.Violation.session_id == cls.id),
            and_(cls.is_waiting_for_payment == False, cls.entry_event.is_(None)),
            cls.session_start_time.between(from_date, to_date)
        )

        stats = {
            "total_session": len(results),
            "active_session": sum(1 for result in results if result.is_active),
            "awaiting_payment": sum(1 for result in results if result.is_waiting_for_payment),
            "violation": sum(violation_dict.get(result.id, 0) for result in results),
            "compliant": compliant_count.scalar()
        }
        return results, stats

    @classmethod
    def get_by_date_v2(cls, db: Session, parking_lot_id: int, from_date: datetime, to_date: datetime,
                       page_number: int, page_size: int):

        subquery = exists().where(base.SessionLog.session_id == cls.id)


        results = (db.query(cls).filter(cls.parking_lot_id == parking_lot_id,
                                        cls.session_start_time.between(from_date, to_date),
                                        func.json_typeof(cls.entry_event) != 'null',
                                        cls.deleted_at.is_(None),
                                        subquery)
                   .order_by(desc(cls.session_start_time)).limit(page_size).offset((page_number - 1) * page_size).all())

        ''' Total session '''
        total_violation_count = db.query(func.count(base.Violation.session_id)).filter(
            base.Violation.session_id == cls.id,
            cls.parking_lot_id == parking_lot_id,
            cls.session_start_time.between(from_date, to_date),
            cls.deleted_at.is_(None),
            subquery
        ).scalar()

        ''' Query to get active session count '''
        active_session_count = db.query(func.count(cls.id)).filter(
            cls.parking_lot_id == parking_lot_id,
            cls.is_active == True,  # Filtering for active sessions
            func.json_typeof(cls.entry_event) != 'null',
            cls.deleted_at.is_(None),
            cls.session_start_time.between(from_date, to_date),
            subquery
        ).scalar()

        ''' Query to get awaiting payment count '''
        awaiting_payment_count = db.query(func.count(cls.id)).filter(
            cls.parking_lot_id == parking_lot_id,
            and_(cls.is_waiting_for_payment == True),
            cls.session_start_time.between(from_date, to_date),
            cls.deleted_at.is_(None),
            subquery
        ).scalar()

        ''' Query to get compliant count '''
        compliant_count = db.query(func.count(cls.id)).filter(
            cls.parking_lot_id == parking_lot_id,
            ~exists().where(base.Violation.session_id == cls.id),
            func.json_typeof(cls.entry_event) != 'null',
            cls.session_start_time.between(from_date, to_date),
            cls.deleted_at.is_(None),
            (select(func.count(base.SessionLog.id))
            .where(base.SessionLog.session_id == cls.id)
            .correlate(cls)
            .scalar_subquery()) > 1
        )

        total_records = db.query(func.count(cls.id)).filter(
            cls.parking_lot_id == parking_lot_id,
            func.json_typeof(cls.entry_event) != 'null',
            cls.session_start_time.between(from_date, to_date),
            cls.deleted_at.is_(None),
            subquery
        ).scalar()

        total_pages = ceil(total_records / page_size)

        stats = {
            "total_sessions": total_records,
            "active_sessions": active_session_count,
            "in_grace_period": awaiting_payment_count,
            "violations": total_violation_count,
            "compliant": compliant_count.scalar()
        }

        metadata = {
            "total_records": total_records,
            "total_pages": total_pages,
            "current_page": page_number,
            "page_size": page_size
        }

        return results, stats, metadata


    @classmethod
    def get_by_date_v3(cls, db: Session, parking_lot_id: int, from_date: datetime, to_date: datetime,
                       page_number: int, page_size: int, session_type: str, provider: str, plate_number_or_spot: str):

        # Aliases for tables
        sl = aliased(base.SessionLog)
        s = aliased(cls)
        v = aliased(base.Violation)

        plate_spot_filter = or_(
            s.lpr_number.ilike(f"%{plate_number_or_spot}%"),
            s.parking_spot_name.ilike(f"%{plate_number_or_spot}%")
        ) if plate_number_or_spot else True

        # Create a subquery to first limit the sessions table
        limited_sessions = (
            db.query(s)
            .filter(
                s.parking_lot_id == parking_lot_id,
                s.session_start_time.between(from_date, to_date),
                func.json_typeof(s.entry_event) != "null",
                s.deleted_at.is_(None),
                plate_spot_filter
            )
            .order_by(desc(s.session_start_time))
            .subquery()
        )

        # Aliased session table from the subquery
        s_limited = aliased(s, limited_sessions)

        # Apply additional session-level filters
        filtered_sessions = (
            db.query(s_limited)
            .filter(
                (db.query(v.id).filter(v.session_id == s_limited.id).exists() if session_type == "with_alert" else True),
                (~db.query(v.id).filter(v.session_id == s_limited.id).exists() if session_type == "without_alert" else True),
                (db.query(sl.id).filter(sl.session_id == s_limited.id, sl.provider.in_(provider.split(","))).exists() if provider else True),
                db.query(sl.id).filter(sl.session_id == s_limited.id).exists()
            )
            .order_by(desc(s_limited.session_start_time))
            .limit(page_size)
            .offset((page_number - 1) * page_size)
            .subquery()
        )

        s_final = aliased(s_limited, filtered_sessions)

        # Main query using the filtered session subquery
        query2 = (
            db.query(
                s_final.id.label("session_id"),
                s_final.entry_event,
                s_final.exit_event,
                s_final.lpr_number,
                s_final.spot_id,
                s_final.is_active,
                s_final.parking_lot_id,
                s_final.session_start_time,
                s_final.session_end_time,
                s_final.session_total_time,
                s_final.not_paid_counter,
                s_final.lpr_record_id,
                s_final.total_paid_amount,
                s_final.has_nph_task,
                s_final.parking_spot_name,
                s_final.is_waiting_for_payment,
                sl.id.label("log_id"),
                sl.action_type,
                sl.description,
                sl.provider,
                sl.meta_info,
                sl.created_at.label("log_created_at"),
            )
            .select_from(s_final)
            .outerjoin(sl, sl.session_id == s_final.id)
            .order_by(desc(s_final.session_start_time),
                      case((sl.action_type == enum.EventsForSessionLog.exit.value, 1), else_=0),
                      sl.id)
        )

        # Print the actual SQL query
        #print(query2.statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))

        session_audit = query2.all()

        # filters for count of records
        if provider:
            provider_filter_count = (
                    exists().where(
                        and_(
                            sl.session_id == s.id,
                            sl.provider.in_(provider.split(","))
                        )
                    )
                )
        else:
            provider_filter_count = exists().where(sl.session_id == s.id)

        # Violation filter logic
        if session_type == "with_alert":
            violation_filter_count = exists(
                select(v.session_id).where(v.session_id == s.id).correlate(s)
            )
        elif session_type == "without_alert":
            violation_filter_count = ~exists(
                select(v.session_id).where(v.session_id == s.id).correlate(s)
            )
        else:
            violation_filter_count = None

        ''' Total violation session '''
        total_violation_count_query = (
            db.query(func.count(v.session_id))
            .join(s, v.session_id == s.id)
            .filter(
                s.parking_lot_id == parking_lot_id,
                s.session_start_time.between(from_date, to_date),
                s.deleted_at.is_(None),
                provider_filter_count,
                plate_spot_filter
            )
        )

        if violation_filter_count is not None:
            total_violation_count_query = total_violation_count_query.filter(violation_filter_count)
        total_violation_count = total_violation_count_query.scalar()

        ''' Query to get active session count '''
        active_session_count_query = (
            db.query(func.count(s.id))
            .filter(
                s.parking_lot_id == parking_lot_id,
                s.is_active == True,
                func.json_typeof(s.entry_event) != 'null',
                s.session_start_time.between(from_date, to_date),
                s.deleted_at.is_(None),
                provider_filter_count,
                plate_spot_filter
            )
        )

        if violation_filter_count is not None:
            active_session_count_query = active_session_count_query.filter(violation_filter_count)
        active_session_count = active_session_count_query.scalar()

        ''' Query to get awaiting payment count '''
        awaiting_payment_count_query = (
            db.query(func.count(s.id))
            .filter(
                s.parking_lot_id == parking_lot_id,
                s.is_waiting_for_payment == True,
                s.session_start_time.between(from_date, to_date),
                s.deleted_at.is_(None),
                provider_filter_count,
                plate_spot_filter
            )
        )

        if violation_filter_count is not None:
            awaiting_payment_count_query = awaiting_payment_count_query.filter(violation_filter_count)
        awaiting_payment_count = awaiting_payment_count_query.scalar()


        total_records_query = db.query(func.count(s.id)).filter(
            s.parking_lot_id == parking_lot_id,
            func.json_typeof(s.entry_event) != 'null',
            s.session_start_time.between(from_date, to_date),
            s.deleted_at.is_(None),
            provider_filter_count,
            plate_spot_filter
        )

        if violation_filter_count is not None:
            total_records_query = total_records_query.filter(violation_filter_count)
        total_records = total_records_query.scalar()

        # print(total_records.statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))

        total_pages = ceil(total_records / page_size)

        stats = {
            "total_sessions": total_records,
            "active_sessions": active_session_count,
            "in_grace_period": awaiting_payment_count,
            "violations": total_violation_count,
            # "compliant": compliant_count.scalar()
        }

        metadata = {
            "total_records": total_records,
            "total_pages": total_pages,
            "current_page": page_number,
            "page_size": page_size
        }

        return session_audit, stats, metadata


    @classmethod
    def get_today_session_with_plate(cls, db: Session, lpr: str, parking_lot_id: int):

        today = datetime.now().date()
        count = (
            db.query(cls)
            .filter(
                cls.lpr_number == lpr,
                func.date(cls.created_at) == today,
                cls.parking_lot_id == parking_lot_id,
            )
            .count()
        )

        if count > 1:
            return True
        else:
            return False

    @classmethod
    def get_session_by_lpr_parking_lot_and_lpr_record_id(cls, db: Session, parking_lot_id: int,
                                                         lpr: str, lpr_record_id: int):

        record_exists = db.query(cls).filter(
            cls.parking_lot_id == parking_lot_id,
            cls.lpr_number == lpr,
            cls.lpr_record_id == lpr_record_id,
            cls.is_active == True
        ).first()

        if record_exists:
            return record_exists
        return None

    @classmethod
    def update_is_waiting_for_payment(cls, db: Session, session):
        session.is_waiting_for_payment = False
        db.commit()

    @classmethod
    def soft_delete_sessions(cls, db: Session, parking_lot_id, delete_upto_datetime=None):
        current_time = datetime.utcnow()
        if delete_upto_datetime:
            db.query(cls).filter(cls.parking_lot_id == parking_lot_id, cls.created_at < delete_upto_datetime).update(
                {cls.deleted_at: current_time}, synchronize_session=False
            )
        else:
            db.query(cls).filter(cls.parking_lot_id == parking_lot_id).update(
                {cls.deleted_at: current_time}, synchronize_session=False)
        db.commit()
