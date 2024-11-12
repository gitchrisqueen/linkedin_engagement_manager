import os

# Broker settings.
broker_url = os.getenv('CELERY_BROKER_URL','redis://redis:6379/0')

## Using the database to store task state and results.
result_backend = os.getenv('CELERY_RESULT_BACKEND','redis://redis:6379/1')

# The Redis backend health checks every 5 minutes (300 seconds)
redis_backend_health_check_interval = 300

timezone = os.getenv('TZ')

broker_connection_retry_on_startup=True

# Set the maximum time in seconds that the ETA scheduler can sleep between rechecking the schedule.
# Default: 1.0 seconds.
worker_timer_precision = 10

# The number of concurrent worker processes/threads/green threads executing tasks.
# Default: Number of CPU cores.
worker_concurrency=1

# How many messages to prefetch at a time multiplied by the number of concurrent processes.
# The default is 4 (four messages for each process)
worker_prefetch_multiplier=1