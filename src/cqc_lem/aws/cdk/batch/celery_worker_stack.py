from aws_cdk import (
    aws_ecs as ecs,
    aws_logs as logs,
    aws_cloudwatch as cloudwatch,
    aws_batch as batch,
    aws_events as events,
    aws_events_targets as targets,
    aws_ec2 as ec2, Duration, Size, CfnOutput, Stack, )
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
        self.celery_batch_job_queue = batch.JobQueue(self, "CeleryWorkerJobQueue")

        # For loop to create Batch Compute Environments
        for i in range(count):
            name = "CeleryWorkerFargateEnv" + str(i)
            fargate_spot_environment = batch.FargateComputeEnvironment(self, name,
                                                                       vpc=props.ec2_vpc,
                                                                       vpc_subnets=ec2.SubnetSelection(
                                                                           subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                                                                       compute_environment_name=name,
                                                                       security_groups=[props.ecs_security_group],
                                                                       spot=True

                                                                       )

            self.celery_batch_job_queue.add_compute_environment(fargate_spot_environment, i)

        # Add a new batch container to the Fargate Task Definition
        container = batch.EcsFargateContainerDefinition(self, "CeleryWorkerFargateContainer",
                                                        image=ecs.ContainerImage.from_docker_image_asset(
                                                            props.ecr_docker_asset),
                                                        command=["/start-celeryworker-solo"],
                                                        cpu=1,  # TODO: Put back to 1 if service doesnt start
                                                        memory=Size.gibibytes(2),
                                                        # TODO": Put back to 2048 if service doesnt start
                                                        execution_role=props.task_execution_role,
                                                        environment={
                                                            # Env passed through props back to service ENV
                                                            "OPENAI_API_KEY": props.open_api_key,
                                                            "LI_CLIENT_ID": props.li_client_id,
                                                            "LI_CLIENT_SECRET": props.li_client_secret,
                                                            "LI_REDIRECT_URI": props.li_redirect_uri,
                                                            "LI_STATE_SALT": props.li_state_salt,
                                                            "LI_API_VERSION": props.li_api_version,
                                                            "PEXELS_API_KEY": props.pexels_api_key,
                                                            "HF_TOKEN": props.hf_token,
                                                            "REPLICATE_API_TOKEN": props.replicate_api_token,
                                                            "RUNWAYML_API_SECRET": props.runwayml_api_secret,
                                                            # ENV set variables above
                                                            "AWS_MYSQL_SECRET_NAME": props.ssm_myql_secret_name,
                                                            "AWS_REGION": props.env.region,
                                                            "CELERY_BROKER_URL": f"redis://{props.redis_url}:{props.redis_port}/0",
                                                            "CELERY_RESULT_BACKEND": f"redis://{props.redis_url}:{props.redis_port}/1",
                                                            "CELERY_QUEUE": "celery",
                                                            "SELENIUM_HUB_HOST": props.elbv2_public_lb.load_balancer_dns_name,
                                                            "SELENIUM_HUB_PORT": str(props.selenium_hub_port),

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
                                                        job_role=props.task_execution_role,
                                                        logging=ecs.LogDriver.aws_logs(
                                                            stream_prefix="celery_worker_logs",
                                                            log_group=logs.LogGroup.from_log_group_arn(
                                                                self, "CeleryWorkerLogGroup",
                                                                log_group_arn=props.celery_worker_log_group_arn
                                                            )
                                                        )

                                                        )

        # Create Batch job definition
        celery_job_def = batch.EcsJobDefinition(self, "CeleryWorkerJobDef",
                                         container=container
                                         )


        # Create metric for number of items in Redis
        queue_items_metric = cloudwatch.Metric(
            namespace="cqc-lem/redis/cache",
            metric_name="CurrItems",
            dimensions_map={
                "CacheClusterId": str(props.redis_cluster_id)
            },
            statistic="Average",
            period=Duration.minutes(1)
        )

        # Alarm for small batch (triggers when there are any items)
        small_jobs_alarm = cloudwatch.Alarm(
            self,
            "CelerySmallJobsAlarm",
            metric=queue_items_metric,
            threshold=1,  # Trigger when there's at least one item
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_name="CelerySmallJobsAlarm",
            alarm_description="Alarm for small amount of jobs in the Celery queue"

        )

        # Alarm for large batch (triggers when there are many items)
        large_jobs_alarm = cloudwatch.Alarm(
            self,
            "CeleryLargeJobsAlarm",
            metric=queue_items_metric,
            threshold=10,  # Adjust this number based on your needs
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            alarm_name="CeleryLargeJobsAlarm",
            alarm_description="Alarm for large amount of jobs in the Celery queue"
        )

        # Create EventBridge rules for small batch
        small_batch_rule = events.Rule(
            self, "SmallBatchRule",
            event_pattern=events.EventPattern(
                source=["aws.cloudwatch"],
                detail_type=["CloudWatch CelerySmallJobsAlarm State Change"],
                detail={
                    "alarmName": [small_jobs_alarm.alarm_name],
                    "state": {
                        "value": ["ALARM"]
                    }
                }
            )
        )

        # Create EventBridge rules for large batch
        large_batch_rule = events.Rule(
            self, "LargeBatchRule",
            event_pattern=events.EventPattern(
                source=["aws.cloudwatch"],
                detail_type=["CloudWatch CeleryLargeJobsAlarm State Change"],
                detail={
                    "alarmName": [large_jobs_alarm.alarm_name],
                    "state": {
                        "value": ["ALARM"]
                    }
                }
            )
        )

        # Add targets for small batch (5 workers)
        small_batch_rule.add_target(targets.BatchJob(
            job_queue_arn=self.celery_batch_job_queue.job_queue_arn,
            job_queue_scope=self.celery_batch_job_queue,
            job_definition_arn=celery_job_def.job_definition_arn,
            job_definition_scope=celery_job_def,
            job_name="small-batch-celery-workers",
            size=5  # Launch 5 workers
        ))

        # Add targets for large batch (10 workers)
        large_batch_rule.add_target(targets.BatchJob(
            job_queue_arn=self.celery_batch_job_queue.job_queue_arn,
            job_queue_scope=self.celery_batch_job_queue,
            job_definition_arn=celery_job_def.job_definition_arn,
            job_definition_scope=celery_job_def,
            job_name="large-batch-celery-workers",
            size=10  # Launch 10 workers
        ))

        # Output resources
        CfnOutput(self, "BatchCeleryJobQueue", value=self.celery_batch_job_queue.job_queue_name)
        CfnOutput(self, "BatchCeleryJobDefinition", value=celery_job_def.job_definition_name)
