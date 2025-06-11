from app.config import huey
from datetime import datetime
from app.models import task


@huey.task()
def schedule_task_on_timestamp(event_obj: event.Task):
    pass
