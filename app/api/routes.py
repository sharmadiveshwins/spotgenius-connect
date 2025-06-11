from fastapi import APIRouter
from app.api import (auth, event, park_pliant, subscribe_api, push_payment_api, session_logs, configure_lot, parking_api,
                     simulation, fake, demo_lot_api)
from app.health import health_check_routes


api_router = APIRouter()


api_router.include_router(auth.auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(event.create_event_router, tags=["Event"])
api_router.include_router(park_pliant.park_pliant, tags=["ParkPliant Callbacks"])
api_router.include_router(subscribe_api.subscribe_api, tags=["Subscribe Api"])
api_router.include_router(push_payment_api.push_payment_router, tags=["Push Api"])
api_router.include_router(session_logs.audit_events_router, tags=["Audit Session Api"])
api_router.include_router(configure_lot.lot, tags=["Configure lot"])
api_router.include_router(parking_api.parking_router, tags=["Parking Api"])
api_router.include_router(fake.fake_router)
api_router.include_router(demo_lot_api.demo_lot_api, tags=["Demo lot API"])
api_router.include_router(health_check_routes, tags=['Container health'])
# Simulator API routes
api_router.include_router(simulation.simulation_router, prefix="/v1/simulation", tags=["Simulation"])
