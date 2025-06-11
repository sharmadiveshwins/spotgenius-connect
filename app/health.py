import logging
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from app.config import redis_client
from app.config import settings
from app.utils.slack_utils import send_slack_notification


logger = logging.getLogger(__name__)


# Configure Redis connection
HEARTBEAT_KEY = "huey_worker_heartbeat"
ALERT_KEY = "huey_worker_health_alert"


health_check_routes= APIRouter()

@health_check_routes.get("/v1/health")
async def health_check():
    try:
        # Check if Redis is reachable
        redis_client.ping()

        # Get the worker heartbeat from Redis
        heartbeat = redis_client.get(HEARTBEAT_KEY)
        if heartbeat:
            heartbeat_time = datetime.fromisoformat(heartbeat)
            now = datetime.utcnow()
            is_worker_healthy = (now - heartbeat_time) < timedelta(minutes=5)
        else:
            is_worker_healthy = False

        # Build the response
        response = {
            "redis": "reachable",
            "worker_status": "healthy" if is_worker_healthy else "unhealthy",
            "last_heartbeat": heartbeat if heartbeat else None,
        }

        if is_worker_healthy:
            if redis_client.get(ALERT_KEY):
                send_slack_notification("🚨 Huey Worker Alert",
                                        "Health Status: healthy \nWorker has recovered and is running normally after a restart.")
            redis_client.delete(ALERT_KEY)
        else:
            alert_count_bytes = redis_client.get(ALERT_KEY)
            alert_count = int(alert_count_bytes) if alert_count_bytes else 0

            if alert_count < settings.SLACK_ALERT_LIMIT:
                send_slack_notification("🚨 Huey Worker Alert",
                                        "Health Status: unhealthy \nHuey worker is unhealthy. Investigate potential resource or dependency issues.")
                redis_client.incr(ALERT_KEY)
                redis_client.expire(ALERT_KEY, settings.SLACK_ALERT_EXPIRY)
            else:
                logger.warning(f"Huey health alert already sent {alert_count} times. Suppressing.")

            raise HTTPException(status_code=500, detail=response)

        return response

    except Exception as e:
        # Handle errors, such as Redis being unavailable
        response = {
            "status": "error",
            "message": str(e),
            "redis": "unreachable",
            "worker_status": "unhealthy",
        }
        raise HTTPException(status_code=500, detail=response)
