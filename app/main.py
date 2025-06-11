import logging
import time
import coloredlogs
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
from huey import crontab
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.config import huey, settings
from app.config import redis_client
from app.exception_handler import custom_exception_handler
from app.api.routes import api_router
from app.models.context_session import get_db_session
from app.service.task_service import TaskService
from app.utils.common import calculate_time_differece
from app.utils.logging.otel_config import setup_telemetry
from app.utils.logging.logging_config import setup_logging
from app.utils.slack_utils import send_slack_notification, get_error_fingerprint


load_dotenv()

app = FastAPI(title="SpotGenius Connect")
app.include_router(api_router, prefix="/api")
app.add_exception_handler(Exception, custom_exception_handler)
# app.mount("/logo", StaticFiles(directory="./app/static/provider_logo"), name="images")
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if settings.ALLOW_OTEL_COLLECTOR.lower() == "true":
    setup_logging()
    setup_telemetry(app)


logger = logging.getLogger(__name__)
log_format = "%(asctime)s : %(levelname).4s - %(message)s - [%(name)s]"
coloredlogs.install(level='debug', isatty=True, fmt=log_format,
                    level_styles={
                        'debug': {'color': 'white', 'bold': True},
                        'info': {'color': 'green', 'bold': True},
                        'error': {'color': 'red', 'bold': True},
                        'warning': {'color': 'yellow', 'bold': True},
                        'critical': {'color': 'red', 'bold': True}})


@app.get("/")
def read_root():
    return {
        "message": "Welcome",
        "description": "spot-connect API.",
        "author": "SpotConnect",
        "documentation": "For API documentation, visit the http://0.0.0.0:8001/docs.",
        "more_info": "Feel free to explore other endpoints",
    }


IMAGES_DIRECTORY = Path("/workspace/app/static/provider_logo/")


@app.get("/api/v1/logo/{image_name}")
async def get_image(image_name: str):
    image_path = IMAGES_DIRECTORY / image_name
    if image_path.exists():
        return FileResponse(str(image_path))
    else:
        return {"error": "Image not found"}


@huey.periodic_task(crontab(minute="*/1"))
def process_task():
    start_time = time.time()
    logging.info("Huey process started.")

    try:
        redis_client.set("huey_worker_heartbeat", datetime.utcnow().isoformat())
        db_session = get_db_session()
        TaskService.process_task(db_session)
    except Exception as e:
        logger.error(f"Error processing task: {e}")

        alert_key = get_error_fingerprint(e)

        alert_count = redis_client.incr(alert_key)
        if alert_count == 1:
            redis_client.expire(alert_key, settings.SLACK_ALERT_EXPIRY)

        logger.critical(f"[Redis] Alert count for '{alert_key}': {alert_count}")

        if alert_count <= settings.SLACK_ALERT_LIMIT:
            send_slack_notification(
                f"🚨 Huey Task Failure",
                f"Task failed with error:\n```{str(e)}```"
            )
        else:
            logger.critical(f"Alert for '{alert_key}' already sent {alert_count} times. Suppressing.")

    total_time = calculate_time_differece(start_time)
    logging.info(f"Huey process completed in {total_time:.2f} seconds.")
