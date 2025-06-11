import logging
from sqlalchemy.orm import Session
from app.utils import enum
from app.utils.email import send_email
from app import schema
from app.models.base import SubTask
from app.models.base import Task, ProviderTypes
from app.models.violation import Violation
from app.utils.common import car_identification_log
import time
from app.utils.common import calculate_time_differece

logger = logging.getLogger(__name__)


class TaskService:

    @staticmethod
    def create_task(db: Session, task_create_schema: schema.TaskCreateSchema, sub_tasks):
        task = Task.create_task(db, task_create_schema)
        if task.status != enum.TaskStatus.COMPLETED.value:
            for sub_task in sub_tasks:
                if isinstance(sub_task, dict):
                    TaskService.create_sub_task(
                        db,
                        task=task,
                        provider_creds_id=sub_task.get('provider_creds_id'),
                        feature_url_path_id=sub_task.get('feature_url_path_id')
                    )
                elif isinstance(sub_task, SubTask):
                    TaskService.create_sub_task(
                        db,
                        task=task,
                        provider_creds_id=sub_task.provider_creds_id,
                        feature_url_path_id=sub_task.feature_url_path
                    )
            return task

    @staticmethod
    def create_sub_task(db, task, provider_creds_id, feature_url_path_id):
        sub_task_schema = schema.SubTaskCreateSchema(provider_creds_id=provider_creds_id,
                                                     feature_url_path=feature_url_path_id,
                                                     task_id=task.id)
        sub_task = SubTask.create_sub_task(db, sub_task_schema)
        return sub_task

    @staticmethod
    def process_task(db: Session):
        """
        function to process all pending tasks scheduled in a defined time frame.
        """
        tasks = Task.get_task_to_execute(db)
        for task in tasks:

            car_identification = car_identification_log(task)

            task_start_time = time.time()
            logger.debug(f"Task: {task.id} / {car_identification} - Task processing begins.")

            provider_type = ProviderTypes.get_by_id(db, task.provider_type)

            if provider_type.text_key == enum.ProviderTypes.PROVIDER_RESERVATION.value and task.status != enum.TaskStatus.CLOSED.value:
                TaskService.process_reservation_task(db, task)

            if provider_type.text_key == enum.ProviderTypes.PAYMENT_PROVIDER.value and task.status != enum.TaskStatus.CLOSED.value:
                TaskService.process_payment_task(db, task)

            if provider_type.text_key == enum.ProviderTypes.PROVIDER_ENFORCEMENT.value and task.status != enum.TaskStatus.CLOSED.value:
                TaskService.process_enforceability_task(db, task)

            if provider_type.text_key == enum.ProviderTypes.PROVIDER_VIOLATION.value and task.status != enum.TaskStatus.CLOSED.value:
                TaskService.process_violation_task(db, task)

            Task.close_task(db, task)
            total_time = calculate_time_differece(task_start_time)
            logging.info(f"Task: {task.id} / {car_identification} - completed in {total_time:.2f} seconds.")

        db.commit()
        db.expire_all()
        db.close_all()


    @staticmethod
    def process_payment_task(db: Session, task):
        sub_tasks = SubTask.get_sub_task_to_process(db, task.id)
        from app.service import FeatureService
        FeatureService.switch_feature(db=db, task=task, sub_task=sub_tasks)

    @staticmethod
    def process_enforceability_task(db: Session, task):

        # violation = Violation.get_violation_by_session_id(db, task.session_id, violation_type=enum.EventTypes.PAYMENT_VIOLATION.value)
        # if violation is not None:
        sub_tasks = SubTask.get_sub_task_to_process(db, task.id)
        from app.service import FeatureService
        FeatureService.switch_feature(db=db, task=task, sub_task=sub_tasks)

    @staticmethod
    def process_reservation_task(db: Session, task):
        sub_tasks = SubTask.get_sub_task_to_process(db, task.id)
        from app.service import FeatureService
        FeatureService.switch_feature(db=db, task=task, sub_task=sub_tasks)

    @staticmethod
    def process_violation_task(db: Session, task):
        sub_tasks = SubTask.get_sub_task_to_process(db, task.id)
        from app.service import FeatureService
        FeatureService.switch_feature(db=db, task=task, sub_task=sub_tasks)

