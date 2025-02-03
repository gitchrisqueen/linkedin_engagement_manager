from aws_cdk import (
    aws_ecs as ecs,
    aws_logs as logs,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_events as events,
    aws_events_targets as targets,
    aws_batch as batch,
    aws_ec2 as ec2, Duration, Size, CfnOutput, Stack, )
from aws_cdk.aws_stepfunctions import DefinitionBody
from constructs import Construct

from cqc_lem.aws.cdk.shared_stack_props import SharedStackProps


class CeleryWorkerStack(Stack):

    def __init__(self, scope: Construct, id: str,
                 props: SharedStackProps,
                 **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # To create number of Batch Compute Environment
        count = 3

        # Create AWS Batch Job Queue
        self.batch_queue = batch.JobQueue(self, "CeleryWorkerJobQueue")

        # For loop to create Batch Compute Environments
        for i in range(count):
            name = "CeleryWorkerFargateEnv" + str(i)
            fargate_spot_environment = batch.FargateComputeEnvironment(self, name,
                                                                       vpc_subnets=ec2.SubnetSelection(
                                                                           subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                                                                       vpc=props.ec2_vpc
                                                                       )

            self.batch_queue.add_compute_environment(fargate_spot_environment, i)

        # Add a new batch container to the Fargate Task Definition
        container = batch.EcsFargateContainerDefinition(self, "CeleryWorkerFargateContainer",
                                                        image=ecs.ContainerImage.from_docker_image_asset(
                                                            props.ecr_docker_asset),
                                                        command=["/start-celeryworker-solo"],
                                                        cpu=2,  # 2 vCPU
                                                        memory=Size.mebibytes(4096),
                                                        # 4GB
                                                        execution_role=props.task_execution_role,
                                                        environment={
                                                            # "AWS_SECRET_NAME": props.ssm_myql_secret_name,
                                                            # "AWS_SQS_QUEUE_URL": props.sqs_queue_url,
                                                            # "AWS_SQS_SECRET_NAME": 'cqc-lem/elasticcache/access',
                                                            "AWS_REGION": props.env.region,
                                                            "CELERY_BROKER_URL": f"redis://{props.redis_url}/0",
                                                            "CELERY_RESULT_BACKEND": f"redis://{props.redis_url}/1",
                                                            "CELERY_QUEUE": "celery",
                                                            # ^^^ Use this to define different priority of queues with more or less processing power
                                                        },
                                                        # Add a new volume to the container
                                                        volumes=[batch.EcsVolume.efs(
                                                            name="CeleryWorkerVolume",
                                                            file_system=props.efs_file_system,
                                                            container_path=props.efs_app_assets_path,
                                                            access_point_id=props.efs_access_point.access_point_id,
                                                            enable_transit_encryption=True,
                                                            use_job_role=True
                                                        )],
                                                        job_role=props.efs_task_role,
                                                        logging=ecs.LogDriver.aws_logs(
                                                            stream_prefix="celery_worker_logs",
                                                            log_group=logs.LogGroup.from_log_group_arn(
                                                                self, "CeleryWorkerLogGroup",
                                                                log_group_arn=props.celery_worker_log_group_arn
                                                            )
                                                        )

                                                        )

        # Create Batch job definition
        job_def = batch.EcsJobDefinition(self, "CeleryWorkerJobDef",
                                         container=container
                                         )

        # Define Step Functions tasks
        get_message_count_task = tasks.LambdaInvoke(self, "Get Message Count",
                                                    lambda_function=props.lambda_get_redis_queue_message_count,
                                                    output_path="$.Payload"
                                                    )

        submit_batch_job_task_small = tasks.BatchSubmitJob(self, "Submit Small Batch Job",
                                                           job_definition_arn=job_def.job_definition_arn,
                                                           job_name="CeleryWorkerJob",
                                                           job_queue_arn=self.batch_queue.job_queue_arn,
                                                           array_size=2
                                                           )

        submit_batch_job_task_large = tasks.BatchSubmitJob(self, "Submit Large Batch Job",
                                                           job_definition_arn=job_def.job_definition_arn,
                                                           job_name="CeleryWorkerJob",
                                                           job_queue_arn=self.batch_queue.job_queue_arn,
                                                           array_size=10
                                                           )

        # Define Step Functions state machine
        definition = get_message_count_task.next(
            sfn.Choice(self, "Message Count Choice")
            .when(sfn.Condition.number_less_than("$.message_count", 10),
                  submit_batch_job_task_small
                  )
            .when(sfn.Condition.number_greater_than_equals("$.message_count", 10),
                  submit_batch_job_task_large
                  )
            .otherwise(sfn.Succeed(self, "No Messages"))
        )

        state_machine = sfn.StateMachine(self, "StateMachine",
                                         definition_body=DefinitionBody.from_chainable(definition),
                                         timeout=Duration.minutes(30)
                                         )

        # Create EventBridge rule to trigger the state machine
        rule = events.Rule(self, "CeleryWorker-5min-event-rule",
                           schedule=events.Schedule.rate(Duration.minutes(5))
                           )

        rule.add_target(targets.SfnStateMachine(state_machine))

        # Output resources
        CfnOutput(self, "BatchCeleryJobQueue", value=self.batch_queue.job_queue_name)
        CfnOutput(self, "BatchCeleryJobDefinition", value=job_def.job_definition_name)
