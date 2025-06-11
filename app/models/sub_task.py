from typing import List

from app.models.base import Base
from sqlalchemy import (Column,
                        String,
                        Integer,
                        ForeignKey, or_, DateTime, and_
                        )
from sqlalchemy.orm import Session
from app import schema
from app.utils import enum
import datetime


class SubTask(Base):
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    status = Column(String, nullable=True, default=enum.SubTaskStatus.PENDING.value)

    task_id = Column(Integer, ForeignKey("task.id"), name="fk_task", nullable=False)
    # provider_id = Column(Integer, ForeignKey("provider.id"), name="fk_provider", nullable=False)
    feature_url_path = Column(Integer, ForeignKey("feature_url_path.id"), name="fk_feature_url_path", nullable=False)
    provider_creds_id = Column(Integer, ForeignKey("provider_creds.id"), name="fk_provider_creds_id",
                         nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    @classmethod
    def create_sub_task(cls, db: Session, sub_task_create_schema: schema.SubTaskCreateSchema):
        """Creates a new sub task."""
        sub_task = SubTask(**sub_task_create_schema.model_dump())
        db.add(sub_task)
        db.commit()
        db.refresh(sub_task)
        return sub_task

    @classmethod
    def get_sub_task_to_process(cls, db: Session, task_id: int):
        all_sub_task = db.query(cls).filter(and_(cls.task_id == task_id))
        all_sub_task.update({cls.status: enum.SubTaskStatus.IN_PROGRESS.value}, synchronize_session=False)
        db.commit()
        return all_sub_task.all()

    @classmethod
    def close_sub_task(cls, db: Session, sub_task_id: int):
        db.query(cls).filter(cls.id == sub_task_id).update({cls.status: enum.SubTaskStatus.CLOSED.value},
                                                           synchronize_session=False)
        db.commit()

    @classmethod
    def close_sub_task_on_paid(cls, db: Session, sub_task_id: int, task_id: int):
        sub_tasks = db.query(cls).filter(cls.task_id == task_id)
        sub_tasks.update({cls.status: enum.SubTaskStatus.CLOSED.value}, synchronize_session=False)
        db.query(cls).filter(cls.id == sub_task_id).update({cls.status: enum.SubTaskStatus.COMPLETED.value},
                                                           synchronize_session=False)
        db.commit()

    @classmethod
    def get_by_id(cls, db: Session, sub_task_id: int):
        sub_task = db.query(cls).get(sub_task_id)
        if sub_task is not None:
            return sub_task

    @classmethod
    def close_sub_task_with_task_id(cls, db: Session, task_ids: List[int]):

        db.query(cls).filter(
            cls.task_id.in_(task_ids),
            or_(cls.status == "PENDING", cls.status == "IN_PROGRESS")
        ).update(
            {cls.status: enum.TaskStatus.CLOSED.value},  # Update status to CLOSED
            synchronize_session=False
        )

    @classmethod
    def soft_delete_sub_task(cls, db: Session, cred_id):

        current_time = datetime.datetime.utcnow()

        db.query(cls).filter(cls.provider_creds_id == cred_id).update(
            {cls.deleted_at: current_time}, synchronize_session=False
        )

        db.commit()