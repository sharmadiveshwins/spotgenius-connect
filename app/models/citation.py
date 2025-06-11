from sqlalchemy import (Column,
                        String,
                        ForeignKey,
                        Integer, Float)
from app.models.base import Base


class Citation(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    plate = Column(String, nullable=False)
    lot_code = Column(String, nullable=False)
    issued = Column(String, nullable=False)
    state = Column(String, nullable=False)
    amount_due = Column(Float, nullable=False)
    violation = Column(Integer, ForeignKey("violation.id"), name="fk_violation_id", nullable=True)

