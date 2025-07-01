# Automated Tracing and Performance Metrics Guide

This document explains how to use the enhanced automated tracing and performance metrics functionality in the LinkedIn Engagement Manager (LEM).

## Overview

The enhanced `jaeger_tracer_helper.py` module provides:

- **Automated Function Tracing**: Decorators to automatically trace function calls
- **Performance Metrics Collection**: Automatic collection of timing, success/failure rates
- **Celery Task Tracing**: Specialized tracing for Celery background tasks
- **Manual Operation Tracing**: Context managers for custom operation tracing
- **Instrumentation Helpers**: Simplified tracing setup for services

## Quick Start

### 1. Basic Function Tracing

```python
from cqc_lem.utilities.jaeger_tracer_helper import trace_function

@trace_function(service_name="user_service")
def update_user_profile(user_id: int, data: dict):
    # Your function logic here
    return updated_profile
```

### 2. Celery Task Tracing

```python
from cqc_lem.utilities.jaeger_tracer_helper import trace_celery_task

@trace_celery_task(service_name="background_tasks")
def process_user_data(self, user_id: int):
    # Your Celery task logic here
    return result
```

### 3. Manual Operation Tracing

```python
from cqc_lem.utilities.jaeger_tracer_helper import trace_operation

def complex_operation():
    with trace_operation("database_query", attributes={"table": "users"}) as span:
        # Your operation logic here
        span.set_attribute("rows_processed", 100)
        return result
```

### 4. Service-Specific Instrumentation Helper

```python
from cqc_lem.utilities.jaeger_tracer_helper import create_instrumentation_helper

# Create a helper for your service
profile_service = create_instrumentation_helper("profile_service")

@profile_service.trace()
def get_user_profile(user_id: int):
    return profile

@profile_service.trace_celery()
def sync_profile(self, user_id: int):
    return result
```

## Detailed Usage

### Function Tracing Decorator

```python
@trace_function(
    service_name="my_service",      # Service name for grouping
    span_name="custom_operation",   # Optional custom span name
    collect_metrics=True,           # Whether to collect performance metrics
    include_args=False              # Whether to include function arguments in traces
)
def my_function(arg1, arg2):
    return result
```

**Parameters:**
- `service_name`: Groups related operations under a service
- `span_name`: Custom name for the trace span (defaults to function name)
- `collect_metrics`: Enable/disable performance metrics collection
- `include_args`: Include function argument metadata in traces (be careful with sensitive data)

### Celery Task Tracing

```python
@trace_celery_task(
    service_name="celery_service",
    include_task_info=True          # Include Celery-specific metadata
)
def my_celery_task(self, param1, param2):
    return result
```

**Automatically captures:**
- Task ID and retry information
- Queue name and routing information
- Task execution time and success/failure

### Manual Operation Tracing

```python
with trace_operation(
    operation_name="complex_process",
    service_name="data_service",
    attributes={                    # Custom attributes
        "user_id": 123,
        "action": "data_export"
    }
) as span:
    # Add more attributes during execution
    span.set_attribute("records_processed", count)
    
    # Your operation logic
    result = perform_operation()
```

## Performance Metrics

### Viewing Metrics

```python
from cqc_lem.utilities.jaeger_tracer_helper import (
    get_performance_metrics,
    log_performance_summary,
    reset_performance_metrics
)

# Get detailed metrics
metrics = get_performance_metrics()
print(f"Total calls: {sum(metrics['function_calls'].values())}")

# Log a summary
log_performance_summary()

# Reset all metrics
reset_performance_metrics()
```

### Metrics Structure

The `get_performance_metrics()` function returns:

```python
{
    'function_calls': {           # Counter of total calls per function
        'module.function_name': 42
    },
    'success_counts': {           # Counter of successful calls
        'module.function_name': 40
    },
    'error_counts': {             # Counter of failed calls
        'module.function_name': 2
    },
    'statistics': {               # Computed timing statistics
        'module.function_name': {
            'avg_ms': 150.5,      # Average execution time
            'min_ms': 10.2,       # Minimum execution time
            'max_ms': 500.8,      # Maximum execution time
            'count': 42,          # Total number of calls
            'total_ms': 6321.0    # Total execution time
        }
    },
    'timestamp': 1641234567.89    # When metrics were collected
}
```

## Integration with Existing Code

### Updating Existing Functions

Before:
```python
def process_linkedin_data(user_id: int):
    # existing logic
    return result
```

After:
```python
@trace_function(service_name="linkedin_service")
def process_linkedin_data(user_id: int):
    # existing logic - no changes needed
    return result
```

### Updating Celery Tasks

Before:
```python
@shared_task.task
def background_process(user_id: int):
    # existing logic
    return result
```

After:
```python
@shared_task.task
@trace_celery_task(service_name="background_service")
def background_process(user_id: int):
    # existing logic - no changes needed
    return result
```

## Environment Configuration

Set these environment variables to configure Jaeger export:

```bash
# Jaeger configuration
export JAEGER_AGENT_HOST="jaeger.example.com"
export JAEGER_SPANS_HTTP_PORT="4318"
export JAEGER_SPANS_GRPC_PORT="4317"

# Enable/disable tracing
export CODE_TRACING="true"
```

If `JAEGER_AGENT_HOST` is not set or empty, traces will be collected but not exported to Jaeger.

## Best Practices

### 1. Service Naming

Use consistent service names to group related functionality:

```python
# Good: Consistent naming
@trace_function(service_name="linkedin_automation")
@trace_function(service_name="linkedin_automation") 

# Avoid: Inconsistent naming
@trace_function(service_name="linkedin")
@trace_function(service_name="automation")
```

### 2. Sensitive Data

Be careful with the `include_args` parameter:

```python
# Safe: No sensitive data in arguments
@trace_function(service_name="user_service", include_args=True)
def get_user_profile(user_id: int):
    pass

# Risky: Password in arguments
@trace_function(service_name="auth_service", include_args=False)  # Don't include args
def authenticate_user(username: str, password: str):
    pass
```

### 3. Performance Impact

- Tracing adds minimal overhead (~1-5ms per operation)
- Metrics collection is thread-safe and efficient
- Use `collect_metrics=False` for high-frequency operations if needed

### 4. Error Handling

Tracing automatically captures exceptions:

```python
@trace_function(service_name="data_service")
def risky_operation():
    if some_condition:
        raise ValueError("Something went wrong")  # Automatically traced
    return "success"
```

## Migration from Manual Tracing

If you have existing manual tracing code, you can gradually migrate:

### Before (Manual):
```python
def my_function():
    tracer = get_jaeger_tracer("service", __name__)
    with tracer.start_as_current_span("operation") as span:
        span.set_attribute("key", "value")
        return do_work()
```

### After (Automated):
```python
@trace_function(service_name="service")
def my_function():
    return do_work()  # Automatically traced

# Or for custom attributes:
def my_function():
    with trace_operation("operation", attributes={"key": "value"}):
        return do_work()
```

## Troubleshooting

### Common Issues

1. **No traces appearing**: Check `JAEGER_AGENT_HOST` environment variable
2. **Import errors**: Ensure OpenTelemetry dependencies are installed
3. **Performance impact**: Use `collect_metrics=False` for high-frequency functions

### Debug Mode

Enable debug logging to see tracing activity:

```python
import logging
logging.getLogger('cqc_lem.utilities.jaeger_tracer_helper').setLevel(logging.DEBUG)
```

## Examples

See `examples/tracing_example.py` for complete working examples of all functionality.

## Integration with CloudWatch

The performance metrics can be integrated with the existing CloudWatch metrics in `my_celery.py`:

```python
from cqc_lem.utilities.jaeger_tracer_helper import get_performance_metrics

def publish_performance_metrics():
    metrics = get_performance_metrics()
    # Publish to CloudWatch using existing infrastructure
```

This enhancement provides comprehensive observability for future development while maintaining compatibility with existing code.