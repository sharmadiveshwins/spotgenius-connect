from app.config import settings
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

# OT Traces import
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# OT Metric import
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

from opentelemetry.instrumentation.requests import RequestsInstrumentor


def setup_telemetry(app):
    # Define a resource to associate telemetry data with the service name
    resource = Resource(attributes={SERVICE_NAME: settings.SERVICE_NAME})

    # Set up Tracing
    span_exporter = OTLPSpanExporter(
        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        insecure=settings.OTEL_COLLECTOR_ALLOW_INSECURE.lower() == "true",
    )
    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer_provider = trace.get_tracer_provider()
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))

    FastAPIInstrumentor().instrument_app(
        app
    )  # instruments FastAPI routes and endpoints to collect trace data
    RequestsInstrumentor().instrument()

    # Set up Metrics
    metric_exporter = OTLPMetricExporter(
        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        insecure=settings.OTEL_COLLECTOR_ALLOW_INSECURE.lower() == "true",
    )
    metric_reader = PeriodicExportingMetricReader(metric_exporter)
    metrics.set_meter_provider(
        MeterProvider(resource=resource, metric_readers=[metric_reader])
    )
