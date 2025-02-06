import os

from aws_cdk import (
    aws_lambda as _lambda,
    aws_ec2 as ec2,
    aws_lambda_python_alpha as _lambda_python_alpha,
    CfnOutput, Stack, Duration, NestedStack, )
from constructs import Construct

from cqc_lem.aws.cdk.shared_stack_props import SharedStackProps


class LambdaStack(NestedStack):

    def __init__(self, scope: Construct, id: str,
                 vpc: ec2.Vpc,
                 redis_url: str,
                 **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create Lambda function
        self.get_queue_message_count = _lambda_python_alpha.PythonFunction(self, "CeleryQueueMessageCountLambda",
                                                                      vpc=vpc,
                                                                      vpc_subnets=ec2.SubnetSelection(one_per_az=True,
                                                                                                      subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),

                                                                      entry=os.path.join(os.path.dirname(__file__),
                                                                                         "lambda"),
                                                                      # Path to the function
                                                                      index="get_redis_queue_message_count.py",
                                                                      # file name
                                                                      handler="lambda_handler",  # function name
                                                                      runtime=_lambda.Runtime.PYTHON_3_13,
                                                                      environment={
                                                                          'CELERY_BROKER_URL': f"redis://{redis_url}:6379/0",
                                                                          'CELERY_QUEUE_NAME': 'celery'
                                                                      },
                                                                      timeout=Duration.seconds(10)
                                                                      )

        '''
        # Create the Lambda function
        initialize_celery_queue_lambda = _lambda.Function(
            self, 'InitializeCeleryQueueLambda',
            runtime=_lambda.Runtime.PYTHON_3_13,
            handler='initialize_celery_queue.handler',
            code=_lambda.Code.from_asset(os.path.join(os.path.dirname(__file__),
                                                      "lambda")),
            timeout=Duration.minutes(5),
            environment={
                'REDIS_URL': f"redis://{props.redis_url}:6379/0"
            }
        )

        # Grant the Lambda function permissions to access Redis
        initialize_celery_queue_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=['elasticache:*'],
                resources=['*']
            )
        )

        # Create the custom resource
        initialize_celery_queue_provider = cr.Provider(
            self, 'InitializeCeleryQueueProvider',
            on_event_handler=initialize_celery_queue_lambda
        )

        initialize_celery_queue = cr.AwsCustomResource(
            self, 'InitializeCeleryQueue',
            service_token=initialize_celery_queue_provider.service_token,
            properties={
                'RedisUrl': props.redis_url
            }
        )
        '''



        # Output resources
        #CfnOutput(self, "MyLambdaFunctionARN", value=self.get_queue_message_count.function_arn)

