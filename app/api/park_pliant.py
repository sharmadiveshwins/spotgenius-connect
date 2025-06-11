from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.dependencies.deps import get_db
from app import schema
from typing import List

from app.service import AuthService
from app.service.park_pliant_service import ParkPliantService
from app.utils import handle_authentication

park_pliant = APIRouter()


@park_pliant.post("/v1/parkpliant/callbacks", response_model=dict)
def register_callbacks(callbacks_schema: schema.Callbacks, db: Session = Depends(get_db)):
    return ParkPliantService.register_callbacks_service(db, callbacks_schema)


@park_pliant.post("/v1/parkpliant/lot/register", response_model=schema.RegisterLotResponseSchema)
def register(register_schema: List[schema.RegisterLotSchema], db: Session = Depends(get_db)):
    return ParkPliantService.register_lot(db, register_schema)


@park_pliant.post("/v1/correct")
def callback_correct(correction_schema: List[schema.Correction], db: Session = Depends(get_db),
                     authorization: str = Depends(AuthService.verify_park_pliant)):
    return ParkPliantService.correction(db, correction_schema)


@park_pliant.post("/v1/pay")
def callback_payment(payment_schema: schema.Payment,
                     db: Session = Depends(get_db),
                     authorization: str = Depends(AuthService.verify_park_pliant)):
    return ParkPliantService.payment(db, payment_schema)


@park_pliant.post("/v1/notice")
def callback_notice(notice_schema: schema.Notice,
                    db: Session = Depends(get_db),
                    authorization: str = Depends(AuthService.verify_park_pliant)):
    return ParkPliantService.notice(db, notice_schema)
