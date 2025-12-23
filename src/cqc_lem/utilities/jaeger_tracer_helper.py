import functools
import os
import time
from collections import Counter, defaultdict
from contextlib import contextmanager
from threading import Lock
from typing import Any, Callable, Dict, Optional

from cqc_lem.utilities.logger import logger

# Performance metrics storage
_metrics_lock = Lock()
_performance_metrics = {
    'function_calls': Counter(),
    'execution_times': defaultdict(list),
    'error_counts': Counter(),
    'success_counts': Counter(),
}
def get_jaeger_tracer(service_name: str, module_name: str) -> Any:
    try:
        from opentelemetry import trace

        # NOTE: Must change http to gprc (or vice versa) in the following import
        # statement to use the proper span exporter
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({
            "service.name": f"cqc-lem.{service_name}",
        })

        tracer_provider = TracerProvider(resource=resource)

        # Only set the tracer provider if one hasn't been set yet
        current_provider = trace.get_tracer_provider()
        if not hasattr(current_provider, 'resource'):  # Not already configured
            trace.set_tracer_provider(tracer_provider)

        # Retrieve Jaeger Configs from environment variables
        jaeger_host = os.getenv("JAEGER_AGENT_HOST")
        jaeger_port = int(os.getenv("JAEGER_SPANS_HTTP_PORT", 4318))
        # jaeger_port2 = int(os.getenv("JAEGER_SPANS_GRPC_PORT", 4317))

        # Only configure the exporter if we have a valid Jaeger host
        if jaeger_host and jaeger_host.lower() not in ['none', 'null', '']:
            # Configure OTel to export traces to Jaeger
            tracer_provider.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(
                        # For using HTTP
                        endpoint=f"http://{jaeger_host}:{jaeger_port}/v1/traces",
                        # For using gRPC:
                        # endpoint=f"http://{jaeger_host}:{jaeger_port2}",
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
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


# Automated tracing decorators and utilities
def trace_function(service_name: str = "default", span_name: Optional[str] = None,
                   collect_metrics: bool = True, include_args: bool = False):
    """
    Decorator to automatically trace function calls with performance metrics.
    
    Args:
        service_name: Service name for the tracer
        span_name: Custom span name (defaults to function name)
        collect_metrics: Whether to collect performance metrics
        include_args: Whether to include function arguments in span attributes
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_jaeger_tracer(service_name, func.__module__ or "default")
            actual_span_name = span_name or f"{func.__name__}"
            
            start_time = time.time()
            function_key = f"{func.__module__}.{func.__name__}"
            
            # Update call count
            if collect_metrics:
                with _metrics_lock:
                    _performance_metrics['function_calls'][function_key] += 1
            
            with tracer.start_as_current_span(actual_span_name) as span:
                try:
                    # Add function metadata to span
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__ or "unknown")
                    span.set_attribute("service.name", service_name)
                    
                    # Optionally include arguments
                    if include_args and hasattr(span, 'set_attribute'):
                        span.set_attribute("function.args_count", len(args))
                        span.set_attribute("function.kwargs_count", len(kwargs))
                        
                        # Add safe string representation of args (avoid sensitive data)
                        if args:
                            span.set_attribute("function.has_args", True)
                        if kwargs:
                            span.set_attribute("function.has_kwargs", True)
                    
                    # Execute the function
                    result = func(*args, **kwargs)
                    
                    # Record success
                    if collect_metrics:
                        with _metrics_lock:
                            _performance_metrics['success_counts'][function_key] += 1
                    
                    span.set_attribute("function.success", True)
                    return result
                    
                except Exception as e:
                    # Record error
                    if collect_metrics:
                        with _metrics_lock:
                            _performance_metrics['error_counts'][function_key] += 1
                    
                    span.set_attribute("function.success", False)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise
                    
                finally:
                    # Record execution time
                    if collect_metrics:
                        execution_time = time.time() - start_time
                        with _metrics_lock:
                            times_list = _performance_metrics['execution_times']
                            times_list[function_key].append(execution_time)
                        
                        span.set_attribute(
                            "function.duration_ms", execution_time * 1000
                        )
        
        return wrapper
    return decorator


def trace_celery_task(service_name: str = "celery", include_task_info: bool = True):
    """
    Specialized decorator for Celery tasks with enhanced task-specific tracing.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self=None, *args, **kwargs):
            tracer = get_jaeger_tracer(service_name, func.__module__ or "celery")
            span_name = f"celery.task.{func.__name__}"
            
            start_time = time.time()
            task_key = f"celery.{func.__name__}"
            
            with _metrics_lock:
                _performance_metrics['function_calls'][task_key] += 1
            
            with tracer.start_as_current_span(span_name) as span:
                try:
                    # Add task-specific metadata
                    span.set_attribute("celery.task.name", func.__name__)
                    span.set_attribute(
                        "celery.task.module", func.__module__ or "unknown"
                    )
                    
                    if include_task_info and self and hasattr(self, 'request'):
                        task_request = self.request
                        span.set_attribute(
                            "celery.task.id", getattr(task_request, 'id', 'unknown')
                        )
                        span.set_attribute(
                            "celery.task.retries", getattr(task_request, 'retries', 0)
                        )
                        
                        # Add queue information if available
                        if hasattr(task_request, 'delivery_info'):
                            delivery_info = task_request.delivery_info
                            if delivery_info and 'routing_key' in delivery_info:
                                span.set_attribute(
                                    "celery.queue.name", delivery_info['routing_key']
                                )
                    
                    # Execute the task
                    if self is not None:
                        result = func(self, *args, **kwargs)
                    else:
                        result = func(*args, **kwargs)
                    
                    with _metrics_lock:
                        _performance_metrics['success_counts'][task_key] += 1
                    
                    span.set_attribute("celery.task.success", True)
                    return result
                    
                except Exception as e:
                    with _metrics_lock:
                        _performance_metrics['error_counts'][task_key] += 1
                    
                    span.set_attribute("celery.task.success", False)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise
                    
                finally:
                    execution_time = time.time() - start_time
                    with _metrics_lock:
                        _performance_metrics['execution_times'][task_key].append(execution_time)
                    
                    span.set_attribute("celery.task.duration_ms", execution_time * 1000)
        
        return wrapper
    return decorator


@contextmanager
def trace_operation(operation_name: str, service_name: str = "default", 
                   attributes: Optional[Dict[str, Any]] = None):
    """
    Context manager for manual tracing of operations.
    
    Args:
        operation_name: Name of the operation to trace
        service_name: Service name for the tracer
        attributes: Additional attributes to add to the span
    """
    tracer = get_jaeger_tracer(service_name, "manual_trace")
    start_time = time.time()
    
    with _metrics_lock:
        _performance_metrics['function_calls'][f"manual.{operation_name}"] += 1
    
    with tracer.start_as_current_span(operation_name) as span:
        try:
            # Add basic attributes
            span.set_attribute("operation.name", operation_name)
            span.set_attribute("operation.type", "manual")
            
            # Add custom attributes
            if attributes:
                for key, value in attributes.items():
                    if value is not None:
                        span.set_attribute(key, value)
            
            yield span
            
            # Record success
            with _metrics_lock:
                _performance_metrics['success_counts'][f"manual.{operation_name}"] += 1
            
            span.set_attribute("operation.success", True)
            
        except Exception as e:
            # Record error
            with _metrics_lock:
                _performance_metrics['error_counts'][f"manual.{operation_name}"] += 1
            
            span.set_attribute("operation.success", False)
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e))
            span.record_exception(e)
            raise
            
        finally:
            execution_time = time.time() - start_time
            with _metrics_lock:
                _performance_metrics['execution_times'][f"manual.{operation_name}"].append(execution_time)
            
            span.set_attribute("operation.duration_ms", execution_time * 1000)


def get_performance_metrics() -> Dict[str, Any]:
    """
    Get collected performance metrics.
    
    Returns:
        Dictionary containing performance metrics including:
        - function_calls: Counter of function call counts
        - execution_times: Lists of execution times per function
        - error_counts: Counter of error counts per function
        - success_counts: Counter of success counts per function
        - statistics: Computed statistics (avg, min, max execution times)
    """
    with _metrics_lock:
        # Compute statistics
        statistics = {}
        for func_name, times in _performance_metrics['execution_times'].items():
            if times:
                statistics[func_name] = {
                    'avg_ms': (sum(times) / len(times)) * 1000,
                    'min_ms': min(times) * 1000,
                    'max_ms': max(times) * 1000,
                    'count': len(times),
                    'total_ms': sum(times) * 1000
                }
        
        return {
            'function_calls': dict(_performance_metrics['function_calls']),
            'error_counts': dict(_performance_metrics['error_counts']),
            'success_counts': dict(_performance_metrics['success_counts']),
            'statistics': statistics,
            'timestamp': time.time()
        }


def reset_performance_metrics():
    """Reset all collected performance metrics."""
    with _metrics_lock:
        _performance_metrics['function_calls'].clear()
        _performance_metrics['execution_times'].clear()
        _performance_metrics['error_counts'].clear()
        _performance_metrics['success_counts'].clear()


def log_performance_summary(logger_func: Optional[Callable] = None):
    """
    Log a summary of performance metrics.
    
    Args:
        logger_func: Optional custom logger function (defaults to the module logger)
    """
    log_func = logger_func or logger.info
    metrics = get_performance_metrics()
    
    if not metrics['statistics']:
        log_func("No performance metrics collected yet.")
        return
    
    log_func("=== Performance Metrics Summary ===")
    
    for func_name, stats in metrics['statistics'].items():
        success_count = metrics['success_counts'].get(func_name, 0)
        error_count = metrics['error_counts'].get(func_name, 0)
        total_calls = success_count + error_count
        success_rate = (success_count / total_calls * 100) if total_calls > 0 else 0
        
        log_func(
            f"{func_name}: "
            f"calls={total_calls}, "
            f"success_rate={success_rate:.1f}%, "
            f"avg={stats['avg_ms']:.2f}ms, "
            f"min={stats['min_ms']:.2f}ms, "
            f"max={stats['max_ms']:.2f}ms"
        )


def create_instrumentation_helper(service_name: str):
    """
    Create a helper object for easier instrumentation of a specific service.
    
    Args:
        service_name: Name of the service
        
    Returns:
        InstrumentationHelper instance
    """
    return InstrumentationHelper(service_name)


class InstrumentationHelper:
    """Helper class to make instrumentation easier for a specific service."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.tracer = get_jaeger_tracer(service_name, "instrumentation_helper")
    
    def trace(self, span_name: Optional[str] = None, collect_metrics: bool = True, 
              include_args: bool = False):
        """Decorator for tracing functions in this service."""
        return trace_function(
            service_name=self.service_name,
            span_name=span_name,
            collect_metrics=collect_metrics,
            include_args=include_args
        )
    
    def trace_celery(self, include_task_info: bool = True):
        """Decorator for tracing Celery tasks in this service."""
        return trace_celery_task(
            service_name=self.service_name,
            include_task_info=include_task_info
        )
    
    def trace_operation(self, operation_name: str,
                        attributes: Optional[Dict[str, Any]] = None):
        """Context manager for tracing operations in this service."""
        return trace_operation(
            operation_name=operation_name,
            service_name=self.service_name,
            attributes=attributes
        )
