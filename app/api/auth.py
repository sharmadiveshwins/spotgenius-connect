from fastapi import APIRouter, Depends

from app import schema
from app import service

auth_router = APIRouter()


@auth_router.post("/token", response_model=schema.SaveToken)
async def auth(request_body: schema.PaymentProviderAuth.ParkMobileSchema,):
    return service.AuthService.auth_impl(request_body)
