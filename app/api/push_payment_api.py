import json
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.dependencies.deps import get_db
from app.schema.push_payment_schema import PullPaymentSchema, PullPaymentSchemaBySpot
from app.service.payment_service import PaymentService
from typing import List

push_payment_router = APIRouter()


async def check(request: Request):
    full_urls = request.url
    print("Full URL:", full_urls)
    body_bytes = await request.body()
    body_str = body_bytes.decode('utf-8')
    print("Full Body:", json.loads(body_str))
    return request


@push_payment_router.post("/v1/check_payment")
async def check_payment_by_plate_number(request_body: PullPaymentSchema, db: Session = Depends(get_db)):
    return PaymentService.check_payment_service(request_body, db)

@push_payment_router.post("/v1/check_payment_by_spot")
async def check_payment_by_spot(request_body: PullPaymentSchemaBySpot, db: Session = Depends(get_db)):
    return PaymentService.check_payment_service_by_spot(request_body, db)
