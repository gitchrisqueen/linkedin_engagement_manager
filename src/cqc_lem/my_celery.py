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
            'schedule': timedelta(minutes=5),  # TODO: change back to 5 Check every 5 minutes
        },
        'send-appreciation-dms': {
            'task': 'cqc_lem.run_scheduler.start_appreciate_dms',
            'schedule': crontab(hour='8', minute='0'),  # Run every day at 8:00 AM
        },
        # Generate Content Plan on the 1st of the month at 1:00 AM
        'generate-content-plan': {
            'task': 'cqc_lem.run_content_plan.generate_content',
            'schedule': crontab(hour='1', minute='0', day_of_month='1'),
        },
        # Create weekly content from plan on Saturdays at 1:00 AM
        'create-content-from-plan': {
            'task': 'cqc_lem.run_content_plan.create_weekly_content',
            'schedule': crontab(hour='1', minute='0', day_of_week='sat'),
        }

    }
)

# Iterate through all modules in the cqc_lem namespace
for _, module_name, _ in pkgutil.iter_modules(cqc_lem.__path__, cqc_lem.__name__ + "."):
    module = importlib.import_module(module_name)
    for name, obj in inspect.getmembers(module):
        if inspect.isfunction(obj) and hasattr(obj, 'shared_task'):
            globals()[name] = obj  # Register the function with the decorator to use in Celery worker
