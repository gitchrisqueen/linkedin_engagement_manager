from aws_cdk import (
    Duration,
    aws_ecs as ecs,
    aws_logs as logs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ec2 as ec2, Stack, RemovalPolicy, )
from constructs import Construct

from cqc_lem.aws.cdk.shared_stack_props import SharedStackProps


class CeleryFlowerStack(Stack):

    def __init__(self, scope: Construct, id: str,
                 props: SharedStackProps,
                 **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a new Fargate Task Definition
        task_definition = ecs.FargateTaskDefinition(
            self, 'CeleryFlowerFargateTaskDef',
            family='celery_flower',
            cpu=256,
            memory_limit_mib=512,
            task_role=props.task_execution_role

        )

        # Add a new volume to the Fargate Task Definition
        task_definition.add_volume(
            name=props.efs_volume_name,
            efs_volume_configuration=props.efs_volume_configuration,
        )

        # Add a new container to the Fargate Task Definition
        celery_flower_container = task_definition.add_container("CeleryFlowerContainer",
                                                                container_name="celery_flower",
                                                                image=ecs.ContainerImage.from_docker_image_asset(
                                                                    props.ecr_docker_asset),
                                                                command=["/start-flower-no-wait"],  # Custom command
                                                                environment={
                                                                    # "AWS_SQS_QUEUE_URL": props.sqs_queue_url,
                                                                    "AWS_REGION": props.env.region,
                                                                    # "AWS_SQS_SECRET_NAME": 'cqc-lem/elasticcache/access',
                                                                    "CELERY_BROKER_URL": f"redis://{props.redis_url}/0",
                                                                    "CELERY_RESULT_BACKEND": f"redis://{props.redis_url}/1",
                                                                    "FLOWER_UNAUTHENTICATED_API": "True",
                                                                    "FLOWER_PERSISTENT": "True",
                                                                    "FLOWER_SAVE_STATE_INTERVAL": "5000",
                                                                    "CELERY_FLOWER_PORT": "8555",
                                                                    "OPENAI_API_KEY": "needs_to_come_from_secret"
                                                                    # TODO; Update this
                                                                },
                                                                port_mappings=[
                                                                    ecs.PortMapping(
                                                                        container_port=8555,
                                                                        host_port=8555,
                                                                        name="celery_flower"  # Name of the port mapping
                                                                    )
                                                                ],
                                                                logging=ecs.LogDriver.aws_logs(
                                                                    stream_prefix="celery_flower_logs",
                                                                    log_group=logs.LogGroup(
                                                                        self, "CeleryFlowerLogGroup",
                                                                        log_group_name="/cqc-lem/celery_flower",
                                                                        retention=logs.RetentionDays.ONE_WEEK,
                                                                        removal_policy=RemovalPolicy.DESTROY
                                                                    )
                                                                )
                                                                )

        # Add a new volume to the Fargate Task Definition
        celery_flower_container.add_mount_points(props.ecs_mount_point)

        # Create a service definitions and port mappings
        celery_flower_service = ecs.FargateService(
            self, 'CeleryFlowerService',
            cluster=props.ecs_cluster,
            task_definition=task_definition,
            desired_count=1,
            max_healthy_percent=200,
            min_healthy_percent=100,

            vpc_subnets=ec2.SubnetSelection(one_per_az=True, subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[props.ecs_security_group],
            service_connect_configuration=ecs.ServiceConnectProps(
                namespace=props.ecs_default_cloud_map_namespace.namespace_name,
                services=[ecs.ServiceConnectService(
                    port_mapping_name="celery_flower",  # Logical name for the service
                    port=8555,  # Container port
                )]),
            service_name="celery-flower-service")
        '''

        # TODO: Figure out this auto scaling

        # Create a new Fargate Service with ALB
        web_app_service = ecs_patterns.ApplicationMultipleTargetGroupsFargateService.ApplicationLoadBalancedFargateService(
            self, 'WebAppService',
            cluster=cluster,
            desired_count=1,
            task_definition=task_definition,
            task_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
            ),
            platform_version=ecs.FargatePlatformVersion.LATEST,
            public_load_balancer=True,
            enable_execute_command=True,
            enable_ecs_managed_tags=True,
            service_name="web-app-service"

        )



        # Create a new Auto Scaling Policy for the ECS Service
        scalable_target = web_app_service.service.auto_scale_task_count(
            min_capacity=1,
            max_capacity=20,
        )

        # Create a new Auto Scaling Policy for the ECS Service
        scalable_target.scale_on_cpu_utilization("CpuScaling",
                                                 target_utilization_percent=50,
                                                 )

        # Create a new Auto Scaling Policy for the ECS Service
        scalable_target.scale_on_memory_utilization("MemoryScaling",
                                                    target_utilization_percent=50,
                                                    )

         '''

        # Allow the ECS Service to connect to the EFS
        # web_app_service.service.connections.allow_from(file_system, ec2.Port.tcp(2049))
        celery_flower_service.connections.allow_from(props.efs_file_system, ec2.Port.tcp(2049))

        # Allow the EFS to connect to the ECS Service
        # web_app_service.service.connections.allow_to(file_system, ec2.Port.tcp(2049))
        celery_flower_service.connections.allow_to(props.efs_file_system, ec2.Port.tcp(2049))

        target_group = elbv2.ApplicationTargetGroup(
            self, "CeleryFlowerTargetGroup",
            target_group_name="celery-flower-target-group",
            vpc=props.ec2_vpc,
            port=8555,
            targets=[celery_flower_service],
            # targets=[celery_flower_service.service],
            target_type=elbv2.TargetType.IP,
            protocol=elbv2.ApplicationProtocol.HTTP,
            health_check=elbv2.HealthCheck(
                path="/",
                port="8555",
                interval=Duration.seconds(60),
                timeout=Duration.seconds(5),
                healthy_threshold_count=2,
                unhealthy_threshold_count=2,
            ),
        )
        target_group.set_attribute(key="deregistration_delay.timeout_seconds",
                                   value="120")

        lb_rule = elbv2.ApplicationListenerRule(
            self, "CeleryFlowerListenerRule",
            listener=props.elbv2_flower_listener,
            priority=3,
            action=elbv2.ListenerAction.forward(target_groups=[target_group]),
            conditions=[elbv2.ListenerCondition.path_patterns(["*"])],
        )
