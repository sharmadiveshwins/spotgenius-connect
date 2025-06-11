import json
from typing import List
from sqlalchemy import (Column,
                        Integer,
                        Text,
                        ForeignKey
                        )
from sqlalchemy.orm import Session
from app.models.base import Base
from app import schema


class AuditRequestResponse(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    api_request = Column(Text, nullable=False)
    api_response = Column(Text, nullable=True)
    api_response_code = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    provider_connect_id = Column(Integer, ForeignKey("provider_connect.id"),
                                 name="fk_provider_connect", nullable=False)
    task_id = Column(Integer, ForeignKey("task.id"), name="fk_task", nullable=False)
    violation_id = Column(Integer, ForeignKey("violation.id"), name="fk_violation", nullable=True)

    @classmethod
    def create(cls, db: Session, audit_schema: schema.AuditReqRespCreateSchema):
        audit_request_response = cls(**audit_schema.model_dump())
        db.add(audit_request_response)
        db.commit()
        db.refresh(audit_request_response)
        return audit_request_response


    @classmethod
    def update(cls, db: Session, id: int, schema: json):
        audit_obj = db.query(cls).get(id)
        audit_obj.response_json = json.dumps(schema)
        db.add(audit_obj)
        db.commit()
        db.refresh(audit_obj)
        return audit_obj

    @classmethod
    def create_audit_req_resp(cls, db: Session, schema: List[schema.RegisterLotSchema]):
        request_schemas = AuditRequestResponse(request_schema=json.dumps(schema))
        db.add(request_schemas)
        db.commit()
        db.refresh(request_schemas)
        return request_schemas
