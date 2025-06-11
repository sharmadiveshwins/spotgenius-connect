from sqlalchemy import (Column,
                        String,
                        Integer,
                        TIMESTAMP,
                        Boolean,
                        ForeignKey,
                        )
from app.models.base import Base
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from datetime import datetime, timedelta


class PushPayment(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    start_date_time = Column(TIMESTAMP, nullable=False)
    end_date_time = Column(TIMESTAMP, nullable=False)
    price_paid = Column(String, nullable=False)
    plate_number = Column(String, nullable=True)
    spot_id = Column(String, nullable=True)
    original_response = Column(String, nullable=False)
    is_checked = Column(Boolean, nullable=False, default=False)
    external_reference_id = Column(Integer, nullable=True)
    location_id = Column(Integer, nullable=True)

    provider_id = Column(Integer, ForeignKey("provider.id"), name="fk_provider_id", nullable=False)

    @classmethod
    def create(cls, db, schema):
        push_payment = PushPayment(**schema.model_dump())
        db.add(push_payment)
        db.commit()
        db.refresh(push_payment)
        return push_payment

    @classmethod
    def get_by_id(cls, db: Session, push_payment: int):
        arrive_obj = db.query(cls).get(push_payment)
        return arrive_obj

    # @classmethod
    # def check_payment(cls, db: Session, plate_number: str, provider_id: int):
    #     arrive_obj = (db.query(cls).filter(and_(cls.plate_number.ilike(plate_number),
    #                                             cls.is_checked.is_(False),
    #                                             cls.provider_id == provider_id))
    #                   .order_by(desc(cls.id)).first())
    #     if arrive_obj:
    #         return arrive_obj

    @classmethod
    def check_payment(cls, db: Session,
                      plate_number: str,
                      provider_id: int,
                      location_id: int = None,
                      is_in_out: bool = None
                      ):

        filters = [cls.plate_number.ilike(plate_number), cls.provider_id == provider_id]

        if location_id is not None:
            filters.append(cls.location_id == location_id)

        if is_in_out is not True:
            filters.append(cls.is_checked.is_(False))

        arrive_obj = (db.query(cls).filter(and_(*filters)).order_by(desc(cls.id)).first())

        return arrive_obj

    @classmethod
    def check_payment_by_spot(cls, db: Session, spot_id: str, provider_id: int, location_id: int = None,is_in_out: bool = None):

        filters = [
            cls.spot_id.ilike(spot_id),
            cls.provider_id == provider_id
        ]

        if location_id is not None:
            filters.append(cls.location_id == location_id)

        if is_in_out is not True:
            filters.append(cls.is_checked.is_(False))

        arrive_obj = (db.query(cls)
                      .filter(and_(*filters))
                      .order_by(desc(cls.id))
                      .first())

        return arrive_obj

    @classmethod
    def update_payment_status(cls, db: Session, push_payment_id: int):
        payment_record = db.query(cls).get(push_payment_id)
        if payment_record:
            payment_record.is_checked = True
            db.commit()

    @classmethod
    def fetch_arrive_payments(cls, db: Session, location_id: int):

        current_date = datetime.utcnow()


        result = ((db.query(cls).filter(cls.location_id == location_id)
                  .filter(cls.end_date_time >= current_date))
                  .all())

        return  result







