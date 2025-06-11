from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CreateOrganizationSchema(BaseModel):
    org_id: int
    org_name: Optional[str] = ''
    contact_name: Optional[str] = ''
    contact_email: Optional[str] = ''


class UpdateOrganizationSchema(BaseModel):
    org_name: Optional[str] = ''
    contact_name: Optional[str] = ''
    contact_email: Optional[str] = ''


class OrganizationSchema(BaseModel):
    id: int
    org_id: int
    org_name: Optional[str] = ''
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    created_at: datetime
    updated_at: datetime
