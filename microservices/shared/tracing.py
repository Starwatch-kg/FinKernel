"""OpenTelemetry distributed tracing setup"""

import os

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_tracing(service_name: str, app=None):
    """Setup OpenTelemetry tracing with Jaeger export"""
    jaeger_host = os.getenv("JAEGER_HOST", "jaeger")
    jaeger_port = int(os.getenv("JAEGER_PORT", "6831"))

    resource = Resource(attributes={SERVICE_NAME: service_name})

    provider = TracerProvider(resource=resource)

    jaeger_exporter = JaegerExporter(
        agent_host_name=jaeger_host,
        agent_port=jaeger_port,
    )

    processor = BatchSpanProcessor(jaeger_exporter)
    provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)

    # Auto-instrument libraries
    if app:
        FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    RedisInstrumentor().instrument()

    return trace.get_tracer(service_name)


def instrument_sqlalchemy(engine):
    """Instrument SQLAlchemy engine for tracing"""
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
