from sqlalchemy import (Column,
                        String,
                        Integer,
                        ForeignKey
                        )
from app.models.base import Base
from sqlalchemy.orm import Session

from app import schema


class ViolationConfiguration(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)

    pricing_type = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)
    duration_amount = Column(Integer, nullable=False)

    parking_lot_id = Column(Integer, ForeignKey("connect_parkinglot.id"), name="fk_connect_parkinglot_id",
                            nullable=False)
    
    @classmethod
    def get_violation_by_lot_id(cls, db: Session, lot_id: str):
        return db.query(cls).filter(cls.parking_lot_id == lot_id).first()

    @classmethod
    def create_or_update(cls, db: Session, request: schema.ViolationConfigurationSchema):

        existing_vc = db.query(cls).filter_by(parking_lot_id=request.parking_lot_id).first()

        if existing_vc:
            # Update existing record
            for key, value in request.model_dump().items():
                setattr(existing_vc, key, value)
            db.commit()
            db.refresh(existing_vc)
            return existing_vc
        else:
            # Create a new record
            new_vc = cls(**request.model_dump())
            db.add(new_vc)
            db.commit()
            db.refresh(new_vc)
            return new_vc

    @classmethod
    def create(cls, db, violation_configuration_schema: schema.ViolationConfigurationSchema):
        violation_configuration = cls(**violation_configuration_schema.model_dump())
        db.add(violation_configuration)
        db.commit()
        db.refresh(violation_configuration)
        return violation_configuration