from datetime import datetime
from typing import Any
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy import Column, TIMESTAMP
from sqlalchemy import Column, DateTime, func, event


@as_declarative()
class Base:
    id: Any
    __name__: str

    @declared_attr
    def __tablename__(cls) -> str:
        snake_case_name = "".join(
            ["_" + c.lower() if c.isupper() else c for c in cls.__name__]
        ).strip("_")
        return snake_case_name

    @declared_attr
    def created_at(cls):
        return Column(DateTime, default=lambda: datetime.now().replace(microsecond=0))

    @declared_attr
    def updated_at(cls):
        return Column(DateTime, default=lambda: datetime.now().replace(microsecond=0),
                      onupdate=lambda: datetime.now().replace(microsecond=0))


@event.listens_for(Base, "before_insert")
def before_insert_listener(mapper, connection, target):
    target.created_at = target.created_at.replace(microsecond=0) if target.created_at else datetime.now().replace(
        microsecond=0)


@event.listens_for(Base, "before_update")
def before_update_listener(mapper, connection, target):
    target.updated_at = target.updated_at.replace(microsecond=0) if target.updated_at else datetime.now().replace(
        microsecond=0)
