import os

import boto3
from kombu.utils.url import safequote

# Redis port
REDIS_PORT = os.getenv('REDIS_PORT', '6379')

# Broker settings.
broker_url = os.getenv('CELERY_BROKER_URL', f'redis://redis:{REDIS_PORT}/0')

## Using the database to store task state and results.
result_backend = os.getenv('CELERY_RESULT_BACKEND', f'redis://redis:{REDIS_PORT}/1')

# The Redis backend visibility timout
result_backend_transport_options = {'visibility_timeout': (
        60 * 60 * 3)}  # 3 hours (This is important. If scheduled items arent handled they will duplicate by being sent back to the queue)

# Backend will try to retry on the event of recoverable exceptions instead of propagating the exception. It will use an exponential backoff sleep time between 2 retries.
result_backend_always_retry = True

# This is the maximum of retries in case of recoverable exceptions.
result_backend_max_retries = 3

# The Redis backend health checks every 5 minutes (300 seconds)
redis_backend_health_check_interval = 300

timezone = os.getenv('TZ')

broker_connection_retry_on_startup = True

# Set the maximum time in seconds that the ETA scheduler can sleep between rechecking the schedule.
# Default: 1.0 seconds.
worker_timer_precision = 10

# The number of concurrent worker processes/threads/green threads executing tasks.
# Default: Number of CPU cores.
worker_concurrency = 1
# Turned off for dynamic worker scaling

# How many messages to prefetch at a time multiplied by the number of concurrent processes.
# The default is 4 (four messages for each process)
worker_prefetch_multiplier = 1

# The maximum number of tasks a worker can execute before it’s replaced by a new process.
worker_max_tasks_per_child = 100

# Gets the max between all the parameters of timeout in the tasks
max_timeout = 60 * 30  # This value must be bigger than the maximum soft timeout set for a task to prevent an infinity loop
broker_transport_options = {'visibility_timeout': max_timeout + 60}  # 60 seconds of margin


def get_aws_sqs(queue_name: str,
                #region_name: str,
                session: boto3.session.Session)->dict:
    sqs = session.client(
        service_name='elasticcache',
        #region_name=region_name
    )

    return sqs.get_queue_url(QueueName=queue_name)

task_create_missing_queues = True

# Addition setting for AWS SQS Usage

# !!! NOTE !!! - The setup function below works but flower won't work with SQS and there are still some other bugs with using SQS Queue
def setup_aws_sqs_config():
    sqs_queue_url = os.getenv('AWS_SQS_QUEUE_URL')
    sqs_queue_name = os.getenv('AWS_SQS_QUEUE_NAME')
    aws_region = os.getenv('AWS_REGION')
    sqs_secret_name = os.getenv('AWS_SQS_SECRET_NAME')

    if aws_region:
        try:
            # Get the AWS session
            session = boto3.session.Session(region_name=aws_region)
            aws_access_key = safequote(session.get_credentials().access_key)
            aws_secret_key = safequote(session.get_credentials().secret_key)
            print(f"Session Access Key: {session.get_credentials().access_key}")
            print(f"Session Secret Key: {session.get_credentials().secret_key}")
            print(f"Session Region: {session.region_name}")

            if sqs_queue_name:
                print(f"Queue Name: {sqs_queue_name}")
                sqs_queue_url = get_aws_sqs(queue_name=sqs_queue_name, session=session)['QueueUrl']
                print(f"SQS Queue URL: {sqs_queue_url}")

                # Set broker_url, broker_transport_options and task_create_missing_queues
                broker_url = "elasticcache://"  # Note: Can use this when environment variables AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set
                print(f"Broker URL: {broker_url}")

                broker_transport_options = {
                    "region": aws_region,
                    "aws_access_key_id": aws_access_key,
                    "aws_secret_access_key": aws_secret_key,
                    "predefined_queues": {
                        "celery": {
                            "url": sqs_queue_url,
                            "access_key_id": aws_access_key,
                            "secret_access_key": aws_secret_key,
                        }
                    },
                    'visibility_timeout': 3600,  # 1 hour
                    'polling_interval': 15
                    # 15 seconds to sleep between unsuccessful polls. !More frequent polling is also more expensive, so increasing the polling interval can save you money.
                }

                task_create_missing_queues = False

        except Exception as e:
            print(f"Error getting AWS session: {e}")
            session = None
