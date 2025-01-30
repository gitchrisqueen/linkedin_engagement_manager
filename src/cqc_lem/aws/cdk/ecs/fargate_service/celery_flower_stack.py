from aws_cdk import (
    Duration,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ecr_assets as ecr_assets,
    aws_ec2 as ec2, NestedStack, )
from constructs import Construct


class CeleryFlowerStack(NestedStack):

    def __init__(self, scope: Construct, id: str,
                 vpc: ec2.Vpc,
                 cluster: ecs.Cluster,
                 public_lb_sg: ec2.SecurityGroup,
                 public_lb: elbv2.ApplicationLoadBalancer,
                 ecs_security_group: ec2.SecurityGroup,
                 cloud_map_namespace,  # TODO: Figure out what this type should be
                 ecs_task_iam_role: iam.Role,
                 task_execution_role: iam.Role,
                 repository_image_asset: ecr_assets.DockerImageAsset,
                 efs_volume_name: str,
                 efs_volume_configuration: ecs.EfsVolumeConfiguration,
                 mount_point: ecs.MountPoint,
                 redis_endpoint_address: str,
                 queue_url: str,
                 **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a new Fargate Task Definition
        task_definition = ecs.FargateTaskDefinition(
            self, 'CeleryFlowerFargateTaskDef',
            family='celery_flower',
            cpu=256,
            memory_limit_mib=512,
            task_role=task_execution_role,
            execution_role=ecs_task_iam_role
        )

        # Add a new volume to the Fargate Task Definition
        task_definition.add_volume(
            name=efs_volume_name,
            efs_volume_configuration=efs_volume_configuration,
        )

        # Add a new container to the Fargate Task Definition
        celery_flower_container = task_definition.add_container("CeleryFlowerContainer",
                                                                container_name="celery_flower",
                                                                image=ecs.ContainerImage.from_docker_image_asset(
                                                                    repository_image_asset),
                                                                command=["/start-flower"],  # Custom command
                                                                environment={
                                                                    "CELERY_RESULT_BACKEND": f"{redis_endpoint_address}/1",
                                                                    "CELERY_BROKER_URL": queue_url,
                                                                    "FLOWER_UNAUTHENTICATED_API": "True",
                                                                    "FLOWER_PERSISTENT": "True",
                                                                    "FLOWER_SAVE_STATE_INTERVAL": "5000",
                                                                    "CELERY_FLOWER_PORT": "8555"
                                                                },
                                                                port_mappings=[
                                                                    ecs.PortMapping(
                                                                        container_port=8555,
                                                                        host_port=8555,
                                                                        name="celery_flower",  # Name of the port mapping
                                                                        #protocol= ecs.Protocol.TCP
                                                                    )
                                                                ],
                                                                logging=ecs.LogDriver.aws_logs(
                                                                    stream_prefix="celery-flower-logs"))

        # Add a new volume to the Fargate Task Definition
        celery_flower_container.add_mount_points(mount_point)

        # Create a service definitions and port mappings
        celery_flower_service = ecs.FargateService(
            self, 'CeleryFlowerService',
            cluster=cluster,
            task_definition=task_definition,
            desired_count=1,
            max_healthy_percent=200,
            min_healthy_percent=100,
            vpc_subnets=ec2.SubnetSelection(one_per_az=True, subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[ecs_security_group],
            service_connect_configuration=ecs.ServiceConnectProps(
                namespace=cloud_map_namespace.namespace_name,
                services=[ecs.ServiceConnectService(
                    port_mapping_name="celery_flower",  # Logical name for the service
                    port=8555  # Container port

                )]),
            service_name="celery-flower-service")

        # TODO: Figure out this auto scaling
        # Create a new Auto Scaling Policy for the ECS Service
        '''scalable_target = celery_flower_service.service.auto_scale_task_count(
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

        target_group = elbv2.ApplicationTargetGroup(
            self, "CeleryFlowerTargetGroup",
            target_group_name="celery-flower-target-group",
            vpc=vpc,
            port=8555,
            targets=[celery_flower_service],
            target_type=elbv2.TargetType.IP,
            protocol=elbv2.ApplicationProtocol.HTTP,
            health_check=elbv2.HealthCheck(
                path="/",
                port="8555",
                interval=Duration.seconds(6),
                timeout=Duration.seconds(5),
                healthy_threshold_count=2,
                unhealthy_threshold_count=2,
            ),
        )
        target_group.set_attribute(key="deregistration_delay.timeout_seconds",
                                   value="120")
        public_lb_sg.add_ingress_rule(peer=ec2.Peer.any_ipv4(), connection=ec2.Port.tcp(8555),
                                      description="Allow HTTP traffic")

        listener = public_lb.add_listener("CeleryFlowerListener", port=8555,
                                          protocol=elbv2.ApplicationProtocol.HTTP,
                                          default_action=elbv2.ListenerAction.forward(target_groups=[target_group]))

        lb_rule = elbv2.ApplicationListenerRule(
            self, "CeleryFlowerListenerRule",
            listener=listener,
            priority=3,
            action=elbv2.ListenerAction.forward(target_groups=[target_group]),
            conditions=[elbv2.ListenerCondition.path_patterns(["*"])],
        )
