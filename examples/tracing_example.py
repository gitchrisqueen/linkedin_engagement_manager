#!/usr/bin/env python3
"""
Example usage of the automated tracing and performance metrics functionality.

This script demonstrates how developers can easily add tracing and performance
monitoring to their functions and operations.
"""

import time
import random
from cqc_lem.utilities.jaeger_tracer_helper import (
    trace_function,
    trace_celery_task,
    trace_operation,
    get_performance_metrics,
    log_performance_summary,
    create_instrumentation_helper
)


# Example 1: Basic function tracing
@trace_function(service_name="example_service", include_args=True)
def calculate_fibonacci(n: int) -> int:
    """Calculate Fibonacci number with automatic tracing."""
    if n <= 1:
        return n
    return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)


# Example 2: Celery task tracing
@trace_celery_task(service_name="background_tasks")
def process_user_data(self, user_id: int, data: dict):
    """Example Celery task with tracing."""
    # Simulate processing time
    time.sleep(random.uniform(0.1, 0.3))
    
    if random.random() < 0.1:  # 10% chance of failure
        raise ValueError(f"Failed to process data for user {user_id}")
    
    return {"user_id": user_id, "processed_items": len(data)}


# Example 3: Manual operation tracing
def perform_database_operation(operation_type: str, table_name: str):
    """Example database operation with manual tracing."""
    
    attributes = {
        "db.operation": operation_type,
        "db.table": table_name,
        "db.driver": "mysql"
    }
    
    with trace_operation(f"db_{operation_type}", attributes=attributes) as span:
        # Simulate database work
        time.sleep(random.uniform(0.05, 0.2))
        
        # Add more attributes during execution
        span.set_attribute("db.rows_affected", random.randint(1, 100))
        
        if random.random() < 0.05:  # 5% chance of failure
            raise ConnectionError("Database connection failed")
        
        return f"Successfully performed {operation_type} on {table_name}"


# Example 4: Using InstrumentationHelper for consistent service tracing
profile_service = create_instrumentation_helper("profile_service")

@profile_service.trace(span_name="profile_update")
def update_user_profile(user_id: int, updates: dict):
    """Update user profile with service-specific tracing."""
    time.sleep(random.uniform(0.1, 0.2))
    return f"Updated profile for user {user_id}"

@profile_service.trace_celery()
def sync_profile_to_external_service(self, user_id: int):
    """Sync profile data to external service."""
    time.sleep(random.uniform(0.2, 0.5))
    return f"Synced user {user_id} to external service"


def run_example_operations():
    """Run example operations to demonstrate tracing and metrics."""
    
    print("=== Running Example Operations ===")
    print()
    
    # Run various operations
    operations = [
        lambda: calculate_fibonacci(8),
        lambda: process_user_data(None, 123, {"key": "value", "items": [1, 2, 3]}),
        lambda: perform_database_operation("SELECT", "users"),
        lambda: perform_database_operation("UPDATE", "profiles"),
        lambda: update_user_profile(456, {"name": "John Doe"}),
        lambda: sync_profile_to_external_service(None, 789),
    ]
    
    # Execute operations multiple times
    for i in range(10):
        operation = random.choice(operations)
        try:
            result = operation()
            print(f"✓ Operation {i+1} completed: {str(result)[:50]}...")
        except Exception as e:
            print(f"✗ Operation {i+1} failed: {str(e)[:50]}...")
    
    print()
    print("=== Performance Metrics Summary ===")
    log_performance_summary()
    
    print()
    print("=== Detailed Metrics ===")
    metrics = get_performance_metrics()
    
    print(f"Total function calls: {sum(metrics['function_calls'].values())}")
    print(f"Total successful operations: {sum(metrics['success_counts'].values())}")
    print(f"Total failed operations: {sum(metrics['error_counts'].values())}")
    
    if metrics['statistics']:
        print("\nTop 3 slowest operations:")
        sorted_ops = sorted(
            metrics['statistics'].items(),
            key=lambda x: x[1]['avg_ms'],
            reverse=True
        )[:3]
        
        for op_name, stats in sorted_ops:
            print(f"  {op_name}: {stats['avg_ms']:.2f}ms avg, {stats['count']} calls")


if __name__ == "__main__":
    # Set environment variable to disable actual Jaeger export for this example
    import os
    os.environ["JAEGER_AGENT_HOST"] = ""
    
    run_example_operations()