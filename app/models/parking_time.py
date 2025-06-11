from sqlalchemy.orm import relationship, Session
from app.models.base import Base
from sqlalchemy import Column, Time, Integer, ForeignKey
from app import schema


class ParkingTime(Base):

    id = Column(Integer, primary_key=True, autoincrement=True)
    parking_lot_id = Column(Integer, ForeignKey("connect_parkinglot.id"), name="fk_connect_parkinglot_id",
                        nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    parkinglot = relationship('ConnectParkinglot', back_populates='parking_time_slots')

    @classmethod
    def create(cls, db: Session, parking_time_schema: schema.ParkingTimeSchema):
        parking_time = cls(**parking_time_schema.model_dump())
        db.add(parking_time)
        db.commit()
        db.refresh(parking_time)
        return parking_time

    @classmethod
    def update(cls, db: Session, id: int, update_parking_time: schema.ParkingTimeSchema):
        parking_time = db.query(cls).filter(cls.id == id).first()
        parking_time.start_time = update_parking_time.start_time
        parking_time.end_time = update_parking_time.end_time
        parking_time.parking_lot_id = update_parking_time.parking_lot_id
        db.commit()
        return parking_time

    @classmethod
    def delete(cls, db: Session, parking_lot_id: int, exclude_delete_time_records: tuple):
        db.query(cls).filter(
            cls.parking_lot_id == parking_lot_id,
            cls.id.notin_(exclude_delete_time_records)
        ).delete(synchronize_session=False)
        db.commit()

    @classmethod
    def get_records_order_by_id(cls, db: Session, parking_lot_id: int):
        return db.query(cls).filter(
                    cls.parking_lot_id == parking_lot_id
                ).order_by(
                    cls.id
                ).all()
