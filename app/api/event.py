from typing import List, Union
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import schema
from app.service import event_service
from app.dependencies.deps import get_db


create_event_router = APIRouter()


# @create_event_router.post("/event", response_model=dict)
# def create_event(events: Union[List[schema.SgEventSchema], dict], db: Session = Depends(get_db)):
#     if type(events) == dict:
#         events = [schema.SgEventSchema(**events)]
#     return event_service.EventService.execute_event(events, db)
