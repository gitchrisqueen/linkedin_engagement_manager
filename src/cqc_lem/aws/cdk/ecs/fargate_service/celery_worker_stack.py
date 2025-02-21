from aws_cdk import (
    Duration,
    aws_ecs as ecs,
    aws_logs as logs,
    aws_cloudwatch as cloudwatch,
    aws_applicationautoscaling as applicationautoscaling,
    aws_ec2 as ec2, Stack, RemovalPolicy, )
from constructs import Construct

from cqc_lem.aws.cdk.shared_stack_props import SharedStackProps


class CeleryWorkerStack(Stack):

    def __init__(self, scope: Construct, id: str,
                 props: SharedStackProps,
                 cpu: int = 4096,
                 memory_limit_mib: int = 8192,
                 **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a new Fargate Task Definition
        task_definition = ecs.FargateTaskDefinition(
            self, 'CeleryWorkerFargateTaskDef',
            family='celery_worker',
            cpu=cpu,
            memory_limit_mib=memory_limit_mib,
            task_role=props.task_execution_role

        )

        # Add a new volume to the Fargate Task Definition
        task_definition.add_volume(
            name=props.efs_volume_name,
            efs_volume_configuration=props.efs_volume_configuration,
        )

        # Add a new container to the Fargate Task Definition
        celery_worker_container = task_definition.add_container("CeleryWorkerContainer",
                                                                container_name="celery_worker",
                                                                cpu=max(cpu / 2, 256),
                                                                # Limit to half the task definition CPU
                                                                memory_limit_mib=max(memory_limit_mib / 2, 512),
                                                                # Limit to half the task definition memory

                                                                image=ecs.ContainerImage.from_docker_image_asset(
                                                                    props.ecr_docker_asset),
                                                                command=["/start-celeryworker-solo"],
                                                                environment={
                                                                    # Env passed through props back to service ENV
                                                                    "OPENAI_API_KEY": props.open_api_key,
                                                                    "LI_CLIENT_ID": props.li_client_id,
                                                                    "LI_CLIENT_SECRET": props.li_client_secret,
                                                                    "LI_REDIRECT_URL": props.li_redirect_url,
                                                                    "LI_STATE_SALT": props.li_state_salt,
                                                                    "LI_API_VERSION": props.li_api_version,
                                                                    "PEXELS_API_KEY": props.pexels_api_key,
                                                                    "HF_TOKEN": props.hf_token,
                                                                    "REPLICATE_API_TOKEN": props.replicate_api_token,
                                                                    "RUNWAYML_API_SECRET": props.runwayml_api_secret,
                                                                    "TZ": props.tz,
                                                                    # "CELERY_ENABLE_UTC": "True",
                                                                    "CELERY_TIMEZONE": props.tz,
                                                                    # ENV set variables above
                                                                    "AWS_MYSQL_SECRET_NAME": props.ssm_myql_secret_name,
                                                                    "AWS_REGION": props.env.region,
                                                                    "CELERY_BROKER_URL": f"redis://{props.redis_url}:{props.redis_port}/0",
                                                                    "CELERY_RESULT_BACKEND": f"redis://{props.redis_url}:{props.redis_port}/1",
                                                                    "CELERY_QUEUE": "celery",
                                                                    # ^^^ Use this to define different priority of queues with more or less processing power
                                                                    # "SELENIUM_HUB_HOST": props.elbv2_public_lb.load_balancer_dns_name, # Through the public load balancer
                                                                    "SELENIUM_HUB_HOST": f"selenium_hub.{props.ecs_default_cloud_map_namespace.namespace_name}",
                                                                    # Through the internal load balancer
                                                                    "SELENIUM_HUB_PORT": str(props.selenium_hub_port),
                                                                    "API_BASE_URL": props.api_base_url,
                                                                    "API_PORT": str(props.api_port),
                                                                    "HEADLESS_BROWSER": "FALSE",
                                                                    "CQC_LEM_CHECK_SCHEDULE_DELTA_MINUTES": "60",
                                                                    "CQC_LEM_POST_TIME_DELTA_MINUTES": "80"

                                                                    # TODO: Turn this to true in production

                                                                },
                                                                logging=ecs.LogDriver.aws_logs(
                                                                    stream_prefix="celery_worker_logs",
                                                                    log_group=logs.LogGroup(
                                                                        self, "CeleryWorkerLogGroup",
                                                                        log_group_name="/cqc-lem/celery_worker",
                                                                        retention=logs.RetentionDays.ONE_WEEK,
                                                                        removal_policy=RemovalPolicy.DESTROY
                                                                    )
                                                                ),
                                                                health_check=ecs.HealthCheck(
                                                                    command=["CMD-SHELL",
                                                                             "python -c 'import celery.bin.worker; exit(0)' || exit 1"]
                                                                    , interval=Duration.seconds(15),
                                                                    timeout=Duration.seconds(5),
                                                                    retries=1,
                                                                    start_period=Duration.seconds(30)

                                                                )
                                                                )

        # Add a new volume to the Fargate Task Definition
        celery_worker_container.add_mount_points(props.ecs_asset_mount_point)

        # Create a service definitions and port mappings
        celery_worker_service = ecs.FargateService(
            self, 'CeleryWorkerService',
            cluster=props.ecs_cluster,
            enable_execute_command=False,  # Reduces metrics
            task_definition=task_definition,
            desired_count=1,
            # VVV - Forces a "stop-then-start" deployment pattern - VVV
            max_healthy_percent=100,
            min_healthy_percent=50,
            vpc_subnets=ec2.SubnetSelection(one_per_az=True, subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[props.ecs_security_group,
                             props.get('sel_hub_sg')  # Need the hub security group to allow ingress
                             ],
            service_name="celery-worker-service",
            capacity_provider_strategies=[
                ecs.CapacityProviderStrategy(
                    capacity_provider='FARGATE',
                    base=1,
                    weight=1

                ),
                ecs.CapacityProviderStrategy(
                    capacity_provider='FARGATE_SPOT',
                    weight=4
                )
            ]

        )

        # TODO: already handled - remove - Allow the ECS Service to connect to the EFS
        celery_worker_service.connections.allow_from(props.efs_file_system, ec2.Port.tcp(2049))

        # TODO: already handled - remove - Allow the EFS to connect to the ECS Service
        celery_worker_service.connections.allow_to(props.efs_file_system, ec2.Port.tcp(2049))

        # Create the scalable target
        target = applicationautoscaling.ScalableTarget(
            self, f'celery-worker-scalable-target',
            service_namespace=applicationautoscaling.ServiceNamespace.ECS,
            max_capacity=4, # TODO: Find a good number for max celery workers capacity
            min_capacity=1,
            resource_id=f'service/{props.ecs_cluster.cluster_name}/{celery_worker_service.service_name}',
            scalable_dimension='ecs:service:DesiredCount'
        )

        '''
        # Create the CloudWatch metric for CPU utilization
        worker_utilization_metric = cloudwatch.Metric(
            namespace='AWS/ECS',
            metric_name='CPUUtilization',
            statistic='max',
            period=Duration.minutes(1),
            dimensions_map={
                'ClusterName': props.ecs_cluster.cluster_name,
                'ServiceName': celery_worker_service.service_name
            }
        )

        # Create the scaling policy with steps
        target.scale_on_metric(
            f'celery-worker-step-metric-scaling',
            metric=worker_utilization_metric,
            adjustment_type=applicationautoscaling.AdjustmentType.CHANGE_IN_CAPACITY,
            scaling_steps=[
                applicationautoscaling.ScalingInterval(
                    change=-1,
                    upper=30
                ),
                applicationautoscaling.ScalingInterval(
                    change=1,
                    lower=75
                )
            ],
            cooldown=Duration.seconds(180)
        )
        '''


        scaling_policy = applicationautoscaling.TargetTrackingScalingPolicy(
            self, f"celery_worker-target-cpu-scaling-policy",
            policy_name=f"celery-worker-scalable-target-cpu-scaling",
            scaling_target=target,
            target_value=40.0,  # 40% CPU utilization target
            scale_in_cooldown=Duration.seconds(300),  # 5 minutes
            scale_out_cooldown=Duration.seconds(180),  # 3 minutes
            predefined_metric=applicationautoscaling.PredefinedMetric.ECS_SERVICE_AVERAGE_CPU_UTILIZATION
        )


        queue_length_metric = cloudwatch.Metric(
            namespace="cqc-lem/celery_queue/celery",
            metric_name="QueueLength",
            period=Duration.minutes(2),
            statistic="Maximum",
            dimensions_map={
                "QueueName": "celery"
            }
        )

        # Create the scaling policy with steps based on queue length thresholds
        target.scale_on_metric(
            'celery-worker-queue-length-scaling',
            metric=queue_length_metric,  # Use queue_length_metric instead of worker_utilization_metric
            adjustment_type=applicationautoscaling.AdjustmentType.EXACT_CAPACITY,
            evaluation_periods=2,  # Add this
            datapoints_to_alarm=2,  # Add this
            scaling_steps=[
                applicationautoscaling.ScalingInterval(
                    change=1,  # Minimum 1 worker when queue length < 5
                    upper=5
                ),
                applicationautoscaling.ScalingInterval(
                    change=3,  # 3 workers when queue length 5-25
                    lower=5,
                    upper=25
                ),
                applicationautoscaling.ScalingInterval(
                    change=8,  # 8 workers when queue length 25-100
                    lower=25,
                    upper=100
                ),
                applicationautoscaling.ScalingInterval(
                    change=15,  # 15 workers when queue length 100-200
                    lower=100,
                    upper=200
                ),
                applicationautoscaling.ScalingInterval(
                    change=30,  # 30 workers when queue length > 200
                    lower=200
                )
            ],
            cooldown=Duration.seconds(300)  # Reduce cooldown to make scaling more responsive
        )
