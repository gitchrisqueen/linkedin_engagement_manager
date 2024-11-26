import os

from opentelemetry import trace
# NOTE: Must change http to gprc (or vice versa) in the following import statement to use the proper span exporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


#TODO: Should this be imported in the main module __init__.py ???
# TODO: How can we automate tracing and add performance metrics for down the road development
def get_jaeger_tracer(service_name: str, module_name: str) -> trace.Tracer:
    resource = Resource.create({
        "service.name": f"cqc-lem.{service_name}",
    })

    tracer_provider = TracerProvider(resource=resource)

    trace.set_tracer_provider(tracer_provider)

    # Retrieve Jaeger Configs from environment variables
    jaeger_host = os.getenv("JAEGER_AGENT_HOST")
    jaeger_port = int(os.getenv("JAEGER_SPANS_HTTP_PORT", 4318))
    # jaeger_port2 = int(os.getenv("JAEGER_SPANS_GRPC_PORT", 4317))

    # Configure OTel to export traces to Jaeger
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=f"http://{jaeger_host}:{jaeger_port}/v1/traces",  # For using HTTP
                # endpoint=f"http://{jaeger_host}:{jaeger_port2}", # For using gRPC
            )
        )
    )

    tracer = trace.get_tracer(module_name)

    return tracer
