from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Session, relationship
from app.models.base import Base
from app.schema import CreateOrganizationSchema, UpdateOrganizationSchema


class Organization(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(Integer, nullable=False)
    org_name = Column(String, nullable=True)
    contact_name = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)

    parking_lots = relationship("ConnectParkinglot", back_populates="organization")

    @classmethod
    def create(cls, db: Session, create_organization_schema: CreateOrganizationSchema):
        organization = cls(**create_organization_schema.model_dump())
        db.add(organization)
        db.commit()
        db.refresh(organization)
        return organization

    @classmethod
    def get_org(cls, db, org_id: int):

        org = db.query(cls).filter(cls.org_id == org_id).first()
        if org:
            return org
        return None

    @classmethod
    def update(cls, db: Session, organization_id: int, update_organization_schema: UpdateOrganizationSchema):
        organization = db.query(cls).filter(cls.id == organization_id).first()
        organization.contact_name = update_organization_schema.contact_name
        organization.contact_email = update_organization_schema.contact_email
        db.commit()
        db.refresh(organization)
        return organization
