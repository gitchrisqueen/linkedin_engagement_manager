import os
import redis


def lambda_handler(event, context):
    celery_broker_url = os.getenv('CELERY_BROKER_URL')
    celery_queue_name = os.getenv('CELERY_QUEUE_NAME')

    # celery_broker_url='redis://redis:6379/0' # Delete this is for testing

    # parse the celery broker url into its host,port,and db part
    redis_url = celery_broker_url.split('//')[1].split(':')[0]
    redis_port = celery_broker_url.split(':')[2].split('/')[0]
    redis_db = celery_broker_url.split('/')[3]

    print(f"Redis URL: {redis_url}")
    print(f"Redis Port: {redis_port}")
    print(f"Redis DB: {redis_db}")

    try:
        r = redis.Redis(host=redis_url, port=redis_port, db=redis_db)

        message_count = r.llen(celery_queue_name)  # This is the queue name

        # Close redis connection
        r.close()

        return {
            'statusCode': 200,
            'message_count': message_count
        }

    except Exception as e:
        print(f"Error connecting to Redis: {e}")
        return {
            'statusCode': 500,
            'body': 'Failed to connect to Redis',
            'message_count': 0
        }


if __name__ == '__main__':
    response = lambda_handler({}, "Testing Function")
    print(response['body'])
