import os
from typing import Optional, Any
from contextlib import contextmanager
from cqc_lem.utilities.logger import logger

# TODO: How can we automate tracing and add performance metrics for down the road development
def get_jaeger_tracer(service_name: str, module_name: str) -> Any:
    try:
        from opentelemetry import trace
        # NOTE: Must change http to gprc (or vice versa) in the following import statement to use the proper span exporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

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

    except ImportError:
        logger.debug("Jaeger dependencies not found. Using no-op tracer.")
        return NoOpTracer()


class NoOpTracer:
    """A no-op tracer that implements the basic tracing interface."""

    @contextmanager
    def start_span(self, name: str, **kwargs):
        yield NoOpSpan()

    def start_as_current_span(self, name: str, **kwargs):
        return self.start_span(name, **kwargs)


class NoOpSpan:
    """A no-op span that implements the basic span interface."""

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def record_exception(self, exception: Exception) -> None:
        pass

    def set_status(self, status: Any) -> None:
        pass
