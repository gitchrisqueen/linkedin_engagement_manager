import os

# Redis port
REDIS_PORT = os.getenv('REDIS_PORT', '6379')

# Broker settings.
broker_url = os.getenv('CELERY_BROKER_URL',f'redis://redis:{REDIS_PORT}/0')

## Using the database to store task state and results.
result_backend = os.getenv('CELERY_RESULT_BACKEND',f'redis://redis:{REDIS_PORT}/1')

# The Redis backend visibility timout
result_backend_transport_options = {'visibility_timeout': (60*30)}  # 30 minutes

# Backend will try to retry on the event of recoverable exceptions instead of propagating the exception. It will use an exponential backoff sleep time between 2 retries.
result_backend_always_retry = True

# This is the maximum of retries in case of recoverable exceptions.
result_backend_max_retries=3

# The Redis backend health checks every 5 minutes (300 seconds)
redis_backend_health_check_interval = 300

timezone = os.getenv('TZ')

broker_connection_retry_on_startup=True

# Set the maximum time in seconds that the ETA scheduler can sleep between rechecking the schedule.
# Default: 1.0 seconds.
worker_timer_precision = 10

# The number of concurrent worker processes/threads/green threads executing tasks.
# Default: Number of CPU cores.
#worker_concurrency=1 # Turned off for dynamic worker scaling

# How many messages to prefetch at a time multiplied by the number of concurrent processes.
# The default is 4 (four messages for each process)
worker_prefetch_multiplier=1

# The maximum number of tasks a worker can execute before it’s replaced by a new process.
worker_max_tasks_per_child=25