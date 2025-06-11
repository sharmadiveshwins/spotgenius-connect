import logging
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from huey import RedisHuey
from typing import Union
import redis
load_dotenv()


class Settings(BaseSettings):
    SQLALCHEMY_DATABASE_URI: str = os.getenv("SQLALCHEMY_DATABASE_URI", "")
    SQLALCHEMY_POOL_SIZE: int = int(os.getenv("SQLALCHEMY_POOL_SIZE", 100))
    SQLALCHEMY_POOL_MAX_OVERFLOW: int = int(os.getenv("SQLALCHEMY_POOL_MAX_OVERFLOW", 100))
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = os.getenv("ALGORITHM", "")
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "")
    SMTP_PORT: int = os.getenv("SMTP_PORT", 587)
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    TASK_PICKING_LIMIT: int = os.getenv("TASK_PICKING_LIMIT", 10)
    TOKEN_FOR_CREATE_ALERT_API: str = os.getenv("TOKEN_FOR_CREATE_ALERT_API", "")
    SIMULATION_PAYMENT_STATUS: bool = os.getenv("SIMULATION_PAYMENT_STATUS", False)
    VIOLATION_GRACE_PERIOD: int = os.getenv("VIOLATION_GRACE_PERIOD", 20)
    PARK_PLAINT_BASE_URL: str = os.getenv("PARK_PLAINT_BASE_URL", "")
    PARK_PLAINT_AUTH_USER: str = os.getenv("PARK_PLAINT_AUTH_USER", "")
    PARK_PLAINT_AUTH_PASSWORD: str = os.getenv("PARK_PLAINT_AUTH_PASSWORD", "")
    ARRIVE_AUTH_KEY: str = os.getenv("ARRIVE_AUTH_KEY", "")
    SPOT_GENIUS_API_BASE_URL: str = os.getenv("SPOT_GENIUS_API_BASE_URL", "")
    EVENT_PICKING_LIMIT: int = os.getenv("EVENT_PICKING_LIMIT", 10)
    POSTGRES_PORT: int = os.getenv("POSTGRES_PORT", 5432)
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "")
    REQUEST_ATTEMPTS: int = os.getenv("REQUEST_ATTEMPTS", 3)
    CURRENT_ATTEMPTS: int = os.getenv("CURRENT_ATTEMPTS", 1)
    CALLBACKS_AUTHORIZATION_TOKEN: str = os.getenv("CALLBACKS_AUTHORIZATION_TOKEN", "txA5TnBgryqzRqWIQXa")
    FERNET_ENCRYPTION_KEY: bytes = os.getenv("FERNET_ENCRYPTION_KEY", "2MFDxnfUeYphTn-_Dl-2BL8rXlIadmxvJXXI6bjQ6go=")
    ORDER_BY: str = os.getenv("ORDER_BY", "reservation.check.lpr")

    TIBA_NPA_API_HOST: str = os.getenv("TIBA_NPA_API_HOST", "")
    TIBA_NPA_API_USERNAME: str = os.getenv("TIBA_NPA_API_USERNAME", "")
    TIBA_NPA_API_PASSWORD: str = os.getenv("TIBA_NPA_API_PASSWORD", "")
    TIBA_NPA_API_COUNTERID: str = os.getenv("TIBA_NPA_API_COUNTERID", "")
    TIBA_NPA_API_REASON: str = os.getenv("TIBA_NPA_API_REASON", "")
    TIBA_NPA_API_ADJUSTMENT: bool = os.getenv("TIBA_NPA_API_ADJUSTMENT", False)

    DATA_TICKET_API_KEY: str = os.getenv("DATA_TICKET_API_KEY", "")
    REQUEST_TIMEOUT: int = os.getenv("REQUEST_TIMEOUT", 30)
    SG_ADMIN_API_REQUEST_TIMEOUT: int = os.getenv("SG_ADMIN_API_REQUEST_TIMEOUT", 3)

    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "")
    ALLOW_OTEL_COLLECTOR: str = os.getenv("ALLOW_OTEL_COLLECTOR", "false")
    OTEL_EXPORTER_OTLP_ENDPOINT: str = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    NEW_RELIC_API_KEY: str = os.getenv("NEW_RELIC_API_KEY", "")
    OTEL_COLLECTOR_ALLOW_INSECURE: str = os.getenv(
        "OTEL_COLLECTOR_ALLOW_INSECURE", "false"
    )

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    OTEL_TRACES_SAMPLER: str = os.getenv("OTEL_TRACES_SAMPLER", "")

    DEFAULT_EXTERNAL_API_REQUEST_TIMEOUT_SEC: int = int(
        os.getenv("DEFAULT_EXTERNAL_API_REQUEST_TIMEOUT_SEC", 30)
    )
    VIOLATION_SERVICE_BASE_URL: str = os.getenv("VIOLATION_SERVICE_BASE_URL", "")

    IS_VIOLATION_SERVICE_ENABLED: bool = os.getenv(
        "IS_VIOLATION_SERVICE_ENABLED", "False"
    ).lower() in ("false", "0", "f")

    PAYMENT_SERVICE_BASE_URL: str = os.getenv("PAYMENT_SERVICE_BASE_URL", "")

    PAYMENT_SERVICE_API_KEY: str = os.getenv("PAYMENT_SERVICE_API_KEY", "")
    PAYMENT_SERVICE_BASE_URL: str = os.getenv("PAYMENT_SERVICE_BASE_URL", "")

    PROVIDER_CARDS_NAME: str = os.getenv("PROVIDER_CARDS_NAME", "")
    ENFORCEMENT_SERVICE_API_KEY: str = os.getenv("ENFORCEMENT_SERVICE_API_KEY", "")

    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")
    SLACK_CHANNEL_NAME: str = os.getenv("SLACK_CHANNEL_NAME", "#sg-dev-alerts")
    SLACK_ALERT_LIMIT: int = int(os.getenv("SLACK_ALERT_LIMIT", 3))
    SLACK_ALERT_EXPIRY: int = int(os.getenv("SLACK_ALERT_EXPIRY", 3600))

    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "dev")

    class Config:
        arbitrary_types_allowed = True
        env_file = ".env"


huey_logger = logging.getLogger("huey")
huey_logger.setLevel(logging.ERROR)
huey_logger.propagate = False


huey = RedisHuey("app", host="spot_connect_redis")
redis_client = redis.StrictRedis(host='spot_connect_redis', port=6379, decode_responses=True)
settings = Settings()
