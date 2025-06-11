import logging

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Time, Enum, or_, and_, desc, case
from sqlalchemy.orm import Session, relationship
from starlette.responses import JSONResponse

from app.models.base import Base
from app.schema import CreateParkinglotSchema
from app.utils.enum import ParkingOperations, TimeUnits 
from app.models import base
from app.utils.enum import ProviderTypes


logger = logging.getLogger(__name__)


class ConnectParkinglot(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    parking_lot_id = Column(Integer, nullable=False)
    contact_email = Column(String, nullable=True)
    contact_name = Column(String, nullable=True)
    parking_lot_name = Column(String, nullable=True)
    grace_period = Column(Integer, nullable=False, default=0)
    retry_mechanism = Column(Integer, nullable=True)
    is_in_out_policy = Column(Boolean, nullable=True, default=True)
    organization_id = Column(ForeignKey("organization.id"), name="fk_organization_id", nullable=False)
    parking_operations = Column(Enum(ParkingOperations, create_type=True),
                                           default=ParkingOperations.spot_based_24_hours_free_parking.value,
                                           nullable=False)
    maximum_park_time_in_minutes = Column(Integer, nullable=True)

    organization = relationship("Organization", back_populates="parking_lots")
    parking_time_slots = relationship('ParkingTime', back_populates='parkinglot', order_by="ParkingTime.start_time")

    @classmethod
    def create(cls, db, create_parkinglot_schema: CreateParkinglotSchema):
        connect_parkinglot = cls(**create_parkinglot_schema.model_dump())
        db.add(connect_parkinglot)
        db.commit()
        db.refresh(connect_parkinglot)
        return connect_parkinglot

    @classmethod
    def get_all(cls, db: Session):
        return db.query(cls).all()

    @classmethod
    def get_by_id(cls, db: Session, parking_lot_id: int):
        parking_lot_obj = db.query(cls).filter(cls.id == parking_lot_id).first()
        return parking_lot_obj

    @classmethod
    def get(cls, db: Session, parking_lot_id: int):
        parking_lot_obj = db.query(cls).filter(cls.parking_lot_id == parking_lot_id).first()
        return parking_lot_obj

    @classmethod
    def get_connect_parking_lot_id(cls, db: Session, parking_lot_id: int):
        parking_lot_obj = db.query(cls).filter(cls.parking_lot_id == parking_lot_id).first()
        return parking_lot_obj

    @classmethod
    def insert_parking_lot_id(cls, db: Session, schema):
        try:
            db_obj = cls(**schema)
            db.add(db_obj)
            db.flush()
            # db.commit()
            # db.refresh(db_obj)
            return db_obj
        except Exception as e:
            logger.info(e)

    @classmethod
    def get_parking_lot(cls, db: Session, parking_lot_id: int):
        parking_lot_obj = db.query(cls).filter(cls.parking_lot_id == parking_lot_id).first()
        if parking_lot_obj:
            return parking_lot_obj
        return None

    @classmethod
    def update(cls, db: Session, parking_lot_id: int, to_update):
        try:
            parking_lot = db.query(cls).filter(cls.id == parking_lot_id).first()
            if parking_lot:
                for key, value in to_update.dict(exclude_unset=True).items():
                    setattr(parking_lot, key, value)
                db.commit()
                return parking_lot
            else:
                return JSONResponse(content={"message": f'parking lot is not register with id {parking_lot_id}'},
                                    status_code=404)
        except Exception as e:
            logging.info(e)

    @classmethod
    def get_by_parkinglot_org_id(cls, db: Session, org_id: int):
        parking_lot_obj = db.query(cls).filter(cls.organization_id == org_id).all()
        return parking_lot_obj

    @classmethod
    def get_connect_parkinglot(cls, db: Session, id: int):
        return db.query(cls).get(id)

    @classmethod
    def is_payment_and_reservation_provider_configured(cls, db: Session, parking_lot_id: int):
        return db.query(
                db.query(ConnectParkinglot).join(
                    base.ProviderConnect, ConnectParkinglot.id == base.ProviderConnect.connect_id
                ).join(
                    base.ProviderCreds, base.ProviderCreds.id == base.ProviderConnect.provider_creds_id
                ).filter(
                    and_(
                        ConnectParkinglot.parking_lot_id == parking_lot_id,
                        or_(
                            base.ProviderCreds.text_key.ilike(f'{ProviderTypes.PAYMENT_PROVIDER.value}%'),
                            base.ProviderCreds.text_key.ilike(f'{ProviderTypes.PROVIDER_RESERVATION.value}%')
                        )
                    )
                ).exists()
            ).scalar()


    @classmethod
    def lots_by_org_order_by_grace_period_contact_info(cls, db: Session, org_id: int):
        parking_lot_obj = db.query(cls).filter(
                            cls.organization_id == org_id
                        ).order_by(
                            desc(
                                case(
                                    (
                                        or_(
                                            cls.grace_period != 0,
                                            cls.contact_name != '',
                                            cls.contact_email != '',
                                        ),
                                        1,
                                    ),
                                    else_=0,
                                )
                            )
                        ).all()
        return parking_lot_obj

    @classmethod
    def lot_by_org_filter_by_grace_period_contact_info(cls, db: Session, org_id: int):
        return db.query(cls).filter(
                cls.organization_id == org_id,
                or_(
                    cls.grace_period != 0,
                    cls.contact_name != '',
                    cls.contact_email != ''
                )
            ).first()
