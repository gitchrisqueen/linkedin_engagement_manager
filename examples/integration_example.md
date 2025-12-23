# Example Integration: Before and After

## Before (Existing Code)
```python
@shared_task.task
def test_error_tracing():
    """Generates a traceable error to test the jaeger tracing configs"""
    myprint("Starting test_error_tracing")
    raise ValueError("This is a test error")

@shared_task.task(bind=True, base=QueueOnce, once={'graceful': True, }, reject_on_worker_lost=True)
def auto_check_scheduled_posts(self):
    """Checks if there are any posts to publish."""
    # ... existing implementation
    pass
```

## After (With Automated Tracing)
```python
from cqc_lem.utilities.jaeger_tracer_helper import trace_celery_task

@shared_task.task
@trace_celery_task(service_name="scheduler_tasks")
def test_error_tracing():
    """Generates a traceable error to test the jaeger tracing configs"""
    myprint("Starting test_error_tracing")
    raise ValueError("This is a test error")  # Automatically traced and metrics collected

@shared_task.task(bind=True, base=QueueOnce, once={'graceful': True, }, reject_on_worker_lost=True)
@trace_celery_task(service_name="scheduler_tasks", include_task_info=True)
def auto_check_scheduled_posts(self):
    """Checks if there are any posts to publish."""
    # ... existing implementation - no changes needed
    # Automatically collects:
    # - Execution time
    # - Success/failure rate
    # - Celery task metadata (retries, queue info)
    # - Error details if exceptions occur
    pass
```

## Benefits of the Integration

1. **Zero Logic Changes**: Existing function logic remains unchanged
2. **Automatic Metrics**: Performance data collected automatically
3. **Error Tracking**: Exceptions are automatically captured and traced
4. **Task Metadata**: Celery-specific information is included in traces
5. **Performance Monitoring**: Easy to identify slow or failing operations

## Viewing the Results

```python
from cqc_lem.utilities.jaeger_tracer_helper import log_performance_summary

# View performance summary
log_performance_summary()

# Example output:
# scheduler_tasks.test_error_tracing: calls=5, success_rate=0.0%, avg=1.2ms, min=0.8ms, max=2.1ms
# scheduler_tasks.auto_check_scheduled_posts: calls=10, success_rate=100.0%, avg=2.5s, min=1.2s, max=4.1s
```

This demonstrates the power of the automated tracing system - significant observability improvements with minimal code changes.