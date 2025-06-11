from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
    OTLPLogExporter,
)
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry._logs import set_logger_provider
from app.config import settings
import logging
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from app.models.session import engine
import coloredlogs
import sys

def setup_logging():

    try:
        SystemMetricsInstrumentor().instrument()
        ### SQLAlchemy instrumentation
        SQLAlchemyInstrumentor().instrument(engine=engine)
        # Set up a resource to associate logs with the service
        resource = Resource(attributes={SERVICE_NAME: settings.SERVICE_NAME})

        # Set up OpenTelemetry logger provider and exporter
        log_exporter = OTLPLogExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            insecure=settings.OTEL_COLLECTOR_ALLOW_INSECURE.lower() == "true",
        )
        log_provider = LoggerProvider(resource=resource)
        set_logger_provider(log_provider)

        # # Configure the log processor
        log_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

        # # Set up Python logging
        log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        handler = LoggingHandler(level=log_level, logger_provider=log_provider)
        logging.getLogger().addHandler(handler)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s - %(name)s - %(funcName)s"
        ))
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.addHandler(handler)
        root_logger.addHandler(console_handler)
    except Exception as e:
        print(e)
