import importlib
import inspect
import pkgutil
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab

import cqc_lem
from cqc_lem import celeryconfig

# Create default Celery app
app = Celery(
    'cqc_lem',

)

# Set the Celery configuration
app.config_from_object(celeryconfig)

# When we use the following in Django, it loads all the <appname>.tasks
# files and registers any tasks it finds in them. We can import the
# tasks files some other way if we prefer.
app.autodiscover_tasks()

# Celery configuration
app.conf.update(
    result_expires=3600,
    beat_schedule={
        'check-scheduled-posts': {
            'task': 'cqc_lem.run_scheduler.check_scheduled_posts',
            'schedule': timedelta(minutes=1),  # TODO: cheange back to 5 Check every 5 minutes
        },
        'send-appreciation-dms': {
            'task': 'cqc_lem.run_scheduler.start_appreciate_dms',
            'schedule': crontab(hour='8', minute='0'),  # Run every day at 8:00 AM
        },
    }
)

# Iterate through all modules in the cqc_lem namespace
for _, module_name, _ in pkgutil.iter_modules(cqc_lem.__path__, cqc_lem.__name__ + "."):
    module = importlib.import_module(module_name)
    for name, obj in inspect.getmembers(module):
        if inspect.isfunction(obj) and hasattr(obj, 'shared_task'):
            globals()[name] = obj  # Register the function with the decorator to use in Celery worker
