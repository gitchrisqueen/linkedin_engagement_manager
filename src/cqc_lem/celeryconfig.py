import os

## Broker settings.
broker_url = os.getenv('CELERY_BROKER_URL','redis://redis:6379/0')

# List of modules to import when the Celery worker starts.
#imports = ('cqc_lem.my_celery',)

# Includes tasks from all registered apps
# include = ['cqc_lem.my_celery']

## Using the database to store task state and results.
result_backend = os.getenv('CELERY_RESULT_BACKEND','redis://redis:6379/1')

timezone = os.getenv('TZ')

broker_connection_retry_on_startup=True