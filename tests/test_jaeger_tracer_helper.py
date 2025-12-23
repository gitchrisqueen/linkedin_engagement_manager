"""
Tests for the automated tracing and performance metrics functionality.
"""
import pytest
import time
from unittest.mock import Mock, patch
from cqc_lem.utilities.jaeger_tracer_helper import (
    trace_function,
    trace_celery_task,
    trace_operation,
    get_performance_metrics,
    reset_performance_metrics,
    log_performance_summary,
    create_instrumentation_helper,
    InstrumentationHelper,
    get_jaeger_tracer,
    NoOpTracer,
    NoOpSpan
)


@pytest.fixture
def reset_metrics():
    """Reset performance metrics before each test."""
    reset_performance_metrics()
    yield
    reset_performance_metrics()


class TestBasicFunctionality:
    """Test basic tracing functionality."""
    
    def test_noop_tracer_creation(self):
        """Test that NoOp tracer is created when OpenTelemetry is not available."""
        tracer = get_jaeger_tracer("test", "test_module")
        # Should be NoOpTracer since OpenTelemetry dependencies might not be fully configured
        assert tracer is not None
    
    def test_noop_span_functionality(self):
        """Test NoOpSpan implements all required methods."""
        span = NoOpSpan()
        
        # Test all methods don't raise errors
        span.set_attribute("test", "value")
        span.record_exception(Exception("test"))
        span.set_status("test")
        
        # Test context manager protocol
        with span:
            pass


class TestTraceFunction:
    """Test the trace_function decorator."""
    
    def test_trace_function_basic(self, reset_metrics):
        """Test basic function tracing."""
        
        @trace_function(service_name="test_service")
        def test_func(x, y):
            return x + y
        
        result = test_func(1, 2)
        assert result == 3
        
        # Check metrics were collected
        metrics = get_performance_metrics()
        func_key = f"{test_func.__module__}.{test_func.__name__}"
        assert metrics['function_calls'][func_key] == 1
        assert metrics['success_counts'][func_key] == 1
        assert func_key in metrics['statistics']
    
    def test_trace_function_with_error(self, reset_metrics):
        """Test function tracing with error handling."""
        
        @trace_function(service_name="test_service")
        def failing_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            failing_func()
        
        # Check error metrics
        metrics = get_performance_metrics()
        func_key = f"{failing_func.__module__}.{failing_func.__name__}"
        assert metrics['function_calls'][func_key] == 1
        assert metrics['error_counts'][func_key] == 1
        assert metrics['success_counts'].get(func_key, 0) == 0
    
    def test_trace_function_custom_span_name(self, reset_metrics):
        """Test function tracing with custom span name."""
        
        @trace_function(service_name="test_service", span_name="custom_operation")
        def test_func():
            return "success"
        
        result = test_func()
        assert result == "success"
        
        # Metrics should still use function name
        metrics = get_performance_metrics()
        func_key = f"{test_func.__module__}.{test_func.__name__}"
        assert metrics['function_calls'][func_key] == 1
    
    def test_trace_function_no_metrics(self, reset_metrics):
        """Test function tracing without metrics collection."""
        
        @trace_function(service_name="test_service", collect_metrics=False)
        def test_func():
            return "success"
        
        test_func()
        
        # No metrics should be collected
        metrics = get_performance_metrics()
        assert not metrics['function_calls']
        assert not metrics['statistics']


class TestTraceCeleryTask:
    """Test the trace_celery_task decorator."""
    
    def test_trace_celery_task_basic(self, reset_metrics):
        """Test basic Celery task tracing."""
        
        @trace_celery_task(service_name="celery_test")
        def test_task():
            return "task_result"
        
        result = test_task()
        assert result == "task_result"
        
        # Check metrics
        metrics = get_performance_metrics()
        task_key = f"celery.{test_task.__name__}"
        assert metrics['function_calls'][task_key] == 1
        assert metrics['success_counts'][task_key] == 1
    
    def test_trace_celery_task_with_self(self, reset_metrics):
        """Test Celery task tracing with self parameter."""
        
        @trace_celery_task(service_name="celery_test")
        def test_task(self, param):
            return f"task_result_{param}"
        
        # Mock self object with request attribute
        mock_self = Mock()
        mock_self.request = Mock()
        mock_self.request.id = "test-task-id"
        mock_self.request.retries = 2
        mock_self.request.delivery_info = {"routing_key": "test_queue"}
        
        result = test_task(mock_self, "test")
        assert result == "task_result_test"


class TestTraceOperation:
    """Test the trace_operation context manager."""
    
    def test_trace_operation_basic(self, reset_metrics):
        """Test basic operation tracing."""
        
        with trace_operation("test_operation", service_name="test_service") as span:
            time.sleep(0.01)  # Small delay to test timing
            result = "operation_complete"
        
        assert result == "operation_complete"
        
        # Check metrics
        metrics = get_performance_metrics()
        op_key = "manual.test_operation"
        assert metrics['function_calls'][op_key] == 1
        assert metrics['success_counts'][op_key] == 1
        assert op_key in metrics['statistics']
        assert metrics['statistics'][op_key]['avg_ms'] > 0
    
    def test_trace_operation_with_attributes(self, reset_metrics):
        """Test operation tracing with custom attributes."""
        
        attributes = {
            "user_id": 123,
            "action": "update_profile",
            "version": "1.0"
        }
        
        with trace_operation("test_operation", attributes=attributes) as span:
            result = "success"
        
        assert result == "success"
        
        # Verify metrics were collected
        metrics = get_performance_metrics()
        assert metrics['function_calls']["manual.test_operation"] == 1
    
    def test_trace_operation_with_error(self, reset_metrics):
        """Test operation tracing with error."""
        
        with pytest.raises(RuntimeError):
            with trace_operation("failing_operation") as span:
                raise RuntimeError("Test error")
        
        # Check error metrics
        metrics = get_performance_metrics()
        op_key = "manual.failing_operation"
        assert metrics['function_calls'][op_key] == 1
        assert metrics['error_counts'][op_key] == 1
        assert metrics['success_counts'].get(op_key, 0) == 0


class TestPerformanceMetrics:
    """Test performance metrics functionality."""
    
    def test_get_performance_metrics_structure(self, reset_metrics):
        """Test that performance metrics have expected structure."""
        
        @trace_function()
        def test_func():
            time.sleep(0.01)
            return "result"
        
        test_func()
        
        metrics = get_performance_metrics()
        
        # Check required keys
        assert 'function_calls' in metrics
        assert 'error_counts' in metrics
        assert 'success_counts' in metrics
        assert 'statistics' in metrics
        assert 'timestamp' in metrics
        
        # Check statistics structure
        func_key = f"{test_func.__module__}.{test_func.__name__}"
        stats = metrics['statistics'][func_key]
        assert 'avg_ms' in stats
        assert 'min_ms' in stats
        assert 'max_ms' in stats
        assert 'count' in stats
        assert 'total_ms' in stats
        assert stats['count'] == 1
        assert stats['avg_ms'] > 0
    
    def test_reset_performance_metrics(self, reset_metrics):
        """Test resetting performance metrics."""
        
        @trace_function()
        def test_func():
            return "result"
        
        test_func()
        
        # Verify metrics exist
        metrics = get_performance_metrics()
        assert len(metrics['function_calls']) > 0
        
        # Reset and verify empty
        reset_performance_metrics()
        metrics = get_performance_metrics()
        assert len(metrics['function_calls']) == 0
        assert len(metrics['statistics']) == 0
    
    def test_log_performance_summary(self, reset_metrics, capsys):
        """Test logging performance summary."""
        
        @trace_function()
        def test_func():
            return "result"
        
        # Call function multiple times
        for _ in range(3):
            test_func()
        
        # Create one error
        @trace_function()
        def failing_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            failing_func()
        
        # Test logging with custom logger
        logged_messages = []
        def custom_logger(message):
            logged_messages.append(message)
        
        log_performance_summary(custom_logger)
        
        # Verify log messages
        assert len(logged_messages) > 0
        assert "Performance Metrics Summary" in logged_messages[0]
        
        # Find the test_func metrics line
        test_func_line = None
        for msg in logged_messages:
            if "test_func" in msg:
                test_func_line = msg
                break
        
        assert test_func_line is not None
        assert "calls=3" in test_func_line
        assert "success_rate=100.0%" in test_func_line


class TestInstrumentationHelper:
    """Test the InstrumentationHelper class."""
    
    def test_instrumentation_helper_creation(self):
        """Test creating instrumentation helper."""
        helper = create_instrumentation_helper("test_service")
        assert isinstance(helper, InstrumentationHelper)
        assert helper.service_name == "test_service"
    
    def test_instrumentation_helper_trace_decorator(self, reset_metrics):
        """Test using instrumentation helper trace decorator."""
        helper = create_instrumentation_helper("test_service")
        
        @helper.trace()
        def test_func():
            return "traced"
        
        result = test_func()
        assert result == "traced"
        
        # Verify metrics
        metrics = get_performance_metrics()
        func_key = f"{test_func.__module__}.{test_func.__name__}"
        assert metrics['function_calls'][func_key] == 1
    
    def test_instrumentation_helper_trace_celery(self, reset_metrics):
        """Test using instrumentation helper for Celery tasks."""
        helper = create_instrumentation_helper("celery_service")
        
        @helper.trace_celery()
        def test_task():
            return "celery_traced"
        
        result = test_task()
        assert result == "celery_traced"
        
        # Verify metrics
        metrics = get_performance_metrics()
        task_key = f"celery.{test_task.__name__}"
        assert metrics['function_calls'][task_key] == 1
    
    def test_instrumentation_helper_trace_operation(self, reset_metrics):
        """Test using instrumentation helper for operations."""
        helper = create_instrumentation_helper("operation_service")
        
        with helper.trace_operation("test_op", {"key": "value"}) as span:
            result = "operation_traced"
        
        assert result == "operation_traced"
        
        # Verify metrics
        metrics = get_performance_metrics()
        op_key = "manual.test_op"
        assert metrics['function_calls'][op_key] == 1


class TestIntegration:
    """Integration tests for combined functionality."""
    
    def test_multiple_function_tracing(self, reset_metrics):
        """Test tracing multiple different functions."""
        
        @trace_function(service_name="service1")
        def func1():
            return "result1"
        
        @trace_function(service_name="service2")
        def func2():
            time.sleep(0.01)
            return "result2"
        
        @trace_celery_task(service_name="celery")
        def task1():
            return "task_result"
        
        # Call functions
        func1()
        func2()
        func2()  # Call twice
        task1()
        
        metrics = get_performance_metrics()
        
        # Verify all functions were tracked
        assert len(metrics['function_calls']) == 3
        assert len(metrics['statistics']) == 3
        
        # Verify call counts
        func1_key = f"{func1.__module__}.{func1.__name__}"
        func2_key = f"{func2.__module__}.{func2.__name__}"
        task1_key = f"celery.{task1.__name__}"
        
        assert metrics['function_calls'][func1_key] == 1
        assert metrics['function_calls'][func2_key] == 2
        assert metrics['function_calls'][task1_key] == 1
        
        # Verify timing metrics exist
        assert metrics['statistics'][func1_key]['count'] == 1
        assert metrics['statistics'][func2_key]['count'] == 2
        assert metrics['statistics'][task1_key]['count'] == 1
    
    def test_mixed_success_and_failure(self, reset_metrics):
        """Test tracking both successful and failed operations."""
        
        @trace_function()
        def sometimes_failing_func(should_fail=False):
            if should_fail:
                raise RuntimeError("Intentional failure")
            return "success"
        
        # Mix of success and failure
        sometimes_failing_func(False)
        sometimes_failing_func(False)
        
        with pytest.raises(RuntimeError):
            sometimes_failing_func(True)
        
        metrics = get_performance_metrics()
        func_key = f"{sometimes_failing_func.__module__}.{sometimes_failing_func.__name__}"
        
        assert metrics['function_calls'][func_key] == 3
        assert metrics['success_counts'][func_key] == 2
        assert metrics['error_counts'][func_key] == 1
        assert metrics['statistics'][func_key]['count'] == 3