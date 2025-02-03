import json
import boto3


def lambda_handler(event, context):
    sqs = boto3.client('elasticcache')
    queue_url = event['queue_url']

    response = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=['ApproximateNumberOfMessages']
    )

    message_count = int(response['Attributes']['ApproximateNumberOfMessages'])

    return {
        'statusCode': 200,
        'body': json.dumps({'message_count': message_count})
    }