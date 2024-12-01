from datetime import timedelta

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init
from opentelemetry.instrumentation.celery import CeleryInstrumentor

from cqc_lem import celeryconfig
from cqc_lem.utilities.jaeger_tracer_helper import get_jaeger_tracer
from cqc_lem.utilities.logger import myprint

# Create default Celery app
app = Celery(
    'cqc_lem',

)

# Set the Celery configuration
app.config_from_object(celeryconfig)

# When we use the following in Django, it loads all the <appname>.tasks
# files and registers any tasks it finds in them. We can import the
# tasks files some other way if we prefer.
app.autodiscover_tasks(['cqc_lem'])

# Celery configuration
app.conf.update(
    result_expires=3600,
    beat_schedule={
        # Comment error tracing out
        # 'test-error-tracing': {
        #    'task': 'cqc_lem.run_scheduler.test_error_tracing',
        #    'schedule': timedelta(minutes=1),  # Run every 1 minutes
        # },
        'check-scheduled-posts': {
            'task': 'cqc_lem.run_scheduler.auto_check_scheduled_posts',
            'schedule': timedelta(minutes=10),  # Run every 10 minutes
        },
        'send-appreciation-dms': {
            'task': 'cqc_lem.run_scheduler.automate_appreciate_dms',
            'schedule': crontab(hour='8', minute='0'),  # Run every day at 8:00 AM
        },
        # TODO: Generate Content Plan on the 1st of the month at 1:00 AM
        'generate-content-plan': {
            'task': 'cqc_lem.run_content_plan.auto_generate_content',
            'schedule': crontab(hour='14', minute='20', day_of_month='1'),
        },
        # Create weekly content from plan on Saturdays at 1:00 AM
        'create-content-from-plan': {
            'task': 'cqc_lem.run_content_plan.auto_create_weekly_content',
            'schedule': crontab(hour='1', minute='0', day_of_week='sat'),
        }

    }
)


@worker_process_init.connect(weak=False)
def init_celery_tracing(*args, **kwargs):
    tracer = get_jaeger_tracer("celery_worker", __name__)

    # Instrument Celery
    ci = CeleryInstrumentor()
    ci.instrument()

    with tracer.start_as_current_span("init_celery_tracing"):
        myprint("Instrumented Celery for tracing")
