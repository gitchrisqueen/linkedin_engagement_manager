from aws_cdk import (
    aws_elasticache as elasticache,
    aws_ecs as ecs,
    aws_sqs as sqs,
    aws_lambda as _lambda,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_events as events,
    aws_efs as efs,
    aws_events_targets as targets,
    aws_batch as batch,
    aws_iam as iam,
    aws_ecr_assets as ecr_assets,
    aws_ec2 as ec2, Duration, Size, CfnOutput, NestedStack, )
from aws_cdk.aws_stepfunctions import DefinitionBody
from constructs import Construct


class CeleryStack(NestedStack):

    def __init__(self, scope: Construct, id: str, vpc: ec2.Vpc, task_execution_role: iam.Role,
                 repository_image_asset: ecr_assets.DockerImageAsset,
                 mysql_host: str,
                 file_system: efs.FileSystem,
                 efs_app_assets_path: str,
                 access_point: efs.AccessPoint,
                 EFSTaskRole: iam.Role,
                 **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create SQS queue
        queue = sqs.Queue(self, "CeleryQueue")

        self.queue_url = queue.queue_url

        # Create a new subnet group for the Redis cluster
        redis_subnet_group = elasticache.CfnSubnetGroup(self, "RedisSubnetGroup",
                                                        description="Subnet group for Redis cluster",
                                                        subnet_ids=vpc.select_subnets(
                                                            subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS).subnet_ids
                                                        )

        # Create Elastic Cache Redis Cluster
        redis_cluster = elasticache.CfnCacheCluster(self, "RedisCluster",
                                                    cache_node_type="cache.t2.micro",
                                                    engine="redis",
                                                    num_cache_nodes=1,
                                                    vpc_security_group_ids=[vpc.vpc_default_security_group],
                                                    cache_subnet_group_name=redis_subnet_group.ref
                                                    )

        self.redis_url = redis_cluster.attr_redis_endpoint_address

        # Create Lambda function
        get_queue_message_count = _lambda.Function(self, "GetQueueMessageCount",
                                                   runtime=_lambda.Runtime.PYTHON_3_9,
                                                   handler="get_queue_message_count.lambda_handler",
                                                   code=_lambda.Code.from_asset("lambda"),
                                                   environment={
                                                       'QUEUE_URL': self.queue_url
                                                   }
                                                   )

        # To create number of Batch Compute Environment
        count = 3

        # Create AWS Batch Job Queue
        self.batch_queue = batch.JobQueue(self, "CeleryJobQueue")

        # For loop to create Batch Compute Environments
        for i in range(count):
            name = "CeleryFargateEnv" + str(i)
            fargate_spot_environment = batch.FargateComputeEnvironment(self, name,
                                                                       vpc_subnets=ec2.SubnetSelection(
                                                                           subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                                                                       vpc=vpc
                                                                       )

            self.batch_queue.add_compute_environment(fargate_spot_environment, i)

        # Add a new batch container to the Fargate Task Definition
        container = batch.EcsFargateContainerDefinition(self, "CeleryFargateContainer",
                                                        image=ecs.ContainerImage.from_docker_image_asset(
                                                            repository_image_asset),
                                                        command=["/start-celeryworker"],
                                                        cpu=2,  # 2 vCPU
                                                        memory=Size.mebibytes(4096),
                                                        # 4GB
                                                        execution_role=task_execution_role,
                                                        environment={
                                                            "MYSQL_HOST": mysql_host,
                                                            "MYSQL_PORT": "3306",
                                                            "MYSQL_USER": "user",
                                                            # TODO: Take this out so it uses AWS Secret
                                                            "MYSQL_PASSWORD": "password",
                                                            # TODO: Take this out so it uses AWS Secret
                                                            "AWS_SECRET_NAME": "admin",
                                                            "CELERY_BROKER_URL": self.queue_url,
                                                            "CELERY_RESULT_BACKEND": f"{self.redis_url}/1",
                                                        },
                                                        # Add a new volume to the container
                                                        volumes=[batch.EcsVolume.efs(
                                                            name="CeleryVolume",
                                                            file_system=file_system,
                                                            container_path=efs_app_assets_path,
                                                            access_point_id=access_point.access_point_id,
                                                            enable_transit_encryption=True,
                                                            use_job_role=True
                                                        )],
                                                        job_role=EFSTaskRole

                                                        )

        # Create Batch job definition
        job_def = batch.EcsJobDefinition(self, "CeleryJobDef",
                                         container=container
                                         )

        # Define Step Functions tasks
        get_message_count_task = tasks.LambdaInvoke(self, "Get Message Count",
                                                    lambda_function=get_queue_message_count,
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
                  submit_batch_job_task_small.next(
                      sfn.Wait(self, "Wait Small",
                               time=sfn.WaitTime.duration(Duration.minutes(5))
                               ).next(
                          tasks.LambdaInvoke(self, "Check Message Count Small",
                                             lambda_function=get_queue_message_count,
                                             output_path="$.Payload"
                                             )
                      )
                  )
                  )
            .when(sfn.Condition.number_greater_than_equals("$.message_count", 10),
                  submit_batch_job_task_large.next(
                      sfn.Wait(self, "Wait Large",
                               time=sfn.WaitTime.duration(Duration.minutes(5))
                               ).next(
                          tasks.LambdaInvoke(self, "Check Message Count Large",
                                             lambda_function=get_queue_message_count,
                                             output_path="$.Payload"
                                             )
                      )
                  )
                  )
            .otherwise(sfn.Succeed(self, "No Messages"))
        )

        state_machine = sfn.StateMachine(self, "StateMachine",
                                         definition_body=DefinitionBody.from_chainable(definition),
                                         timeout=Duration.minutes(30)
                                         )

        # Create EventBridge rule to trigger the state machine
        rule = events.Rule(self, "Celery-5min-event-rule",
                           schedule=events.Schedule.rate(Duration.minutes(5))
                           )

        rule.add_target(targets.SfnStateMachine(state_machine))

        # Output resources
        CfnOutput(self, "RedisEndpointAddress", export_name="RedisEndpointAddress", value=self.redis_url)
        CfnOutput(self, "CeleryQueueUrl", export_name="CeleryQueueUrl", value=self.queue_url)
        CfnOutput(self, "BatchJobQueue", value=self.batch_queue.job_queue_name)
        CfnOutput(self, "JobDefinition", value=job_def.job_definition_name)
