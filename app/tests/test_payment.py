from unittest.mock import patch, ANY
from .conftest import client
from app.models.base import Task, SubTask
from app.service.features.check_payment_by_lpr import CheckPaymentByLPR
from app.service.task_service import TaskService


@patch('app.dependencies.deps.get_db')
def test_payment_not_paid(mock_get_db):
    task = Task(id=460, plate_number="ABC123", event_type='car.entry', created_at='2024-03-21 00:04:11.461',
                provider_type=1, parking_lot_id=1, feature_text_key="payment.check.lpr")

    with patch('app.service.payment_service.PaymentService.not_paid') as mock_payment_service_paid:
        TaskService.process_payment_task(mock_get_db, task)
        mock_payment_service_paid.assert_called_once_with(task=task, db=mock_get_db)
