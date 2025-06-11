import unittest
from unittest.mock import Mock
from sqlalchemy.orm import Session
from app.models.base import Task, SubTask
from app.service import TaskService
from app import schema
from app.utils.enum import TaskStatus


class TestTaskService(unittest.TestCase):

    def test_create_task_incomplete_status(self):
        db = Mock(spec=Session)
        task_create_schema = schema.TaskCreateSchema(plate_number="ABC123", event_type='car.entry', created_at='2024-03-21 00:04:11.461',
                provider_type=1, parking_lot_id=1, feature_text_key="payment.check.lpr")
        sub_tasks = [SubTask(task_id=1, provider_creds_id=1, feature_url_path=1),
                     SubTask(task_id=1, provider_creds_id=1, feature_url_path=1)]

        task = Task(id=1, plate_number="ABC123", event_type='car.entry', created_at='2024-03-21 00:04:11.461',
             provider_type=1, parking_lot_id=1, feature_text_key="payment.check.lpr")
        task.status = TaskStatus.IN_PROGRESS.value
        Task.create_task = Mock(return_value=task)

        result = TaskService.create_task(db, task_create_schema, sub_tasks)

        self.assertEqual(result, task)
        Task.create_task.assert_called_with(db, task_create_schema)
