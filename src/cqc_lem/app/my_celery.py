from datetime import timedelta

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init
from opentelemetry.instrumentation.celery import CeleryInstrumentor

from cqc_lem.app import celeryconfig
from cqc_lem.app.celeryconfig import broker_url
from cqc_lem.utilities.env_constants import CODE_TRACING
from cqc_lem.utilities.jaeger_tracer_helper import get_jaeger_tracer
from cqc_lem.utilities.logger import myprint

# Create default Celery app
app = Celery(
    'cqc_lem',
    broker=broker_url,

)

# Set the Celery configuration
app.config_from_object(celeryconfig)

# When we use the following in Django, it loads all the <appname>.tasks
# files and registers any tasks it finds in them. We can import the
# tasks files some other way if we prefer.
app.autodiscover_tasks(['cqc_lem'])

# Setup Celery Once for task that should only be queued once per parameters sent

app.conf.ONCE = {
    'backend': 'celery_once.backends.Redis',  # TODO: What should this be for AWS SQS
    'settings': {
        'url': broker_url,
        'default_timeout': 60 * 60
    }
}

# Celery configuration
app.conf.update(
    result_expires=3600,
    beat_schedule={
        # Comment error tracing out
        # 'test-error-tracing': {
        #    'task': 'cqc_lem.app.run_scheduler.test_error_tracing',
        #    'schedule': timedelta(minutes=1),  # Run every 1 minutes
        # },
        'check-scheduled-posts': {
            'task': 'cqc_lem.app.run_scheduler.auto_check_scheduled_posts',
            'schedule': timedelta(minutes=5)  # Run every 5 minutes
        },
        'generate-content-plan': {
            'task': 'cqc_lem.app.run_content_plan.auto_generate_content',
            'schedule': crontab(hour='1', minute='0')  # Run every day at 1:00 AM
        },
        'create-content-from-plan': {
            'task': 'cqc_lem.app.run_content_plan.auto_create_weekly_content',
            'schedule': crontab(hour='1', minute='30')  # Run every day at 1:30 AM
        },
        'clean-up-stale-invites': {
            'task': 'cqc_lem.app.run_scheduler.auto_clean_stale_invites',
            'schedule': crontab(hour='2', minute='0', )  # Run every day at 2:00 AM
        },
        'clen-up-stale-profiles': {
            'task': 'cqc_lem.app.run_scheduler.auto_clean_stale_profiles',
            'schedule': crontab(hour='3', minute='0', )  # Run every day at 3:00 AM
        },
        'clen-up-old_videos': {
            'task': 'cqc_lem.app.run_scheduler.auto_clean_old_videos',
            'schedule': crontab(hour='4', minute='0', )  # Run every day at 4:00 AM
        },
        'invite_to_company_pages': {
            'task': 'cqc_lem.app.run_scheduler.auto_invite_to_company_pages',
            'schedule': crontab(hour='5', minute='0', day_of_month='1')  # Run on the 1st of the month at 5:00 AM
        },
        'send-appreciation-dms': {
            'task': 'cqc_lem.app.run_scheduler.auto_appreciate_dms',
            'schedule': crontab(hour='8', minute='0')  # Run every day at 8:00 AM
        }

    }
)


@worker_process_init.connect(weak=False)
def restore_all_unacknowledged_messages(*args, **kwargs):
    """
    Restores all the unacknowledged messages in the queue.
    Taken from https://gist.github.com/mlavin/6671079
    """
    conn = app.connection(transport_options={'visibility_timeout': 0})
    qos = conn.channel().qos
    qos.restore_visible()
    myprint('Unacknowledged messages restored')


@worker_process_init.connect(weak=False)
def init_celery_tracing(*args, **kwargs):
    if CODE_TRACING:
        tracer = get_jaeger_tracer("celery_worker", __name__)

        # Instrument Celery
        ci = CeleryInstrumentor()
        ci.instrument()

        with tracer.start_as_current_span("init_celery_tracing"):
            myprint("Instrumented Celery for tracing")
    else:
        myprint("Tracing is disabled")