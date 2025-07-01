# Celery-Once Backend Configuration for AWS SQS

## Problem Statement

The codebase had a TODO comment asking: "What should this be for AWS SQS" in the celery-once backend configuration in `src/cqc_lem/app/my_celery.py`.

## Solution Overview

The key insight is that **Celery broker and celery-once backend are independent concerns**:

- **Celery Broker**: Handles message queuing (Redis, SQS, RabbitMQ, etc.)
- **celery-once Backend**: Handles task deduplication (Redis, File system, etc.)

Therefore, you can use AWS SQS for scalable message brokering while still using Redis for fast, reliable task deduplication.

## Implementation

### Dynamic Configuration Function

Created `get_celery_once_config()` in `src/cqc_lem/app/my_celery.py` that:

1. **Detects broker type** from the `broker_url`
2. **Configures appropriate backend** based on broker
3. **Handles edge cases** and provides fallbacks

### Configuration Logic

| Broker Type | celery-once Backend | Storage Location | Use Case |
|-------------|-------------------|------------------|----------|
| `redis://...` | Redis | Same Redis, DB 2 | Local/dev with Redis |
| `sqs://` | Redis | ElastiCache Redis | AWS production |
| `elasticcache://` | Redis | ElastiCache Redis | Legacy AWS config |
| Unknown | File | `/tmp/celery_once` | Fallback scenario |

### AWS SQS Configuration

For AWS SQS deployments:
- **Broker**: SQS handles message queuing (scalable, managed)
- **celery-once**: Redis (ElastiCache) handles task deduplication (fast, reliable)
- **Environment variables**: `REDIS_HOST` and `REDIS_PORT` can override defaults

## Benefits

1. **Cloud-native scaling**: SQS provides unlimited scaling for message queues
2. **Performance**: Redis provides fast task deduplication lookups
3. **Reliability**: Both services are managed AWS services
4. **Flexibility**: Works with any broker type
5. **Zero config**: Automatically detects and configures appropriate backend

## Files Modified

- `src/cqc_lem/app/my_celery.py`: Added dynamic configuration function
- `src/cqc_lem/app/celeryconfig.py`: Fixed SQS service name bug
- `tests/unit/test_celery_once_config.py`: Comprehensive test suite

## Usage

The configuration is automatic - no code changes needed in application code. The system detects the broker type and configures the appropriate celery-once backend automatically.

## Testing

All scenarios are covered by unit tests:
- Redis brokers with different databases
- SQS brokers
- Authentication scenarios  
- Fallback scenarios
- Custom Redis host/port configurations

Run tests with:
```bash
poetry run python -m pytest tests/unit/test_celery_once_config.py -v
```