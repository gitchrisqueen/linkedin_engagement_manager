import os
from sqlite3.dbapi2 import apilevel

from aws_cdk import (
    Duration,
    aws_ecs as ecs,
    aws_efs as efs,
    aws_iam as iam,
    aws_ecr_assets as ecr_assets,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ec2 as ec2, Stack, )
from constructs import Construct
from openai import api_key


class APIStack(Stack):

    def __init__(self, scope: Construct, id: str,
                 vpc: ec2.Vpc,
                 cluster: ecs.Cluster,
                 file_system: efs.FileSystem,
                 ecs_security_group: ec2.SecurityGroup,
                 cloud_map_namespace: str,
                 task_execution_role: iam.Role,
                 repository_image_asset: ecr_assets.DockerImageAsset,
                 myql_secret_name: str,
                 efs_volume_name: str,
                 efs_volume_configuration: ecs.EfsVolumeConfiguration,
                 mount_point: ecs.MountPoint,
                 api_listener: elbv2.ApplicationListener,
                 **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a new Fargate Task Definition
        task_definition = ecs.FargateTaskDefinition(
            self, 'APIFargateTaskDef',
            family='api',
            cpu=256,
            memory_limit_mib=512,
            task_role=task_execution_role,

        )

        # Add a new volume to the Fargate Task Definition
        task_definition.add_volume(
            name=efs_volume_name,
            efs_volume_configuration=efs_volume_configuration,
        )

        # Add a new container to the Fargate Task Definition
        api_key_container = task_definition.add_container("APIContainer",
                                                          container_name="api",
                                                          image=ecs.ContainerImage.from_docker_image_asset(
                                                              repository_image_asset),
                                                          command=["/start-fastapi"],  # Custom command
                                                          environment={
                                                              "OPENAI_API_KEY": 'needs_to_come_from_aws_secret',
                                                              # TODO: Need to get this ^^^ from file or AWS Secret
                                                              "AWS_MYSQL_SECRET_NAME": myql_secret_name,
                                                              "API_PORT": "8000",
                                                          },
                                                          port_mappings=[
                                                              ecs.PortMapping(
                                                                  container_port=8000,
                                                                  host_port=8000,
                                                                  name="api"  # Name of the port mapping
                                                              )
                                                          ],
                                                          # logging=ecs.LogDriver.aws_logs(stream_prefix="web-app-logs")
                                                          )

        # Add a new volume to the Fargate Task Definition
        api_key_container.add_mount_points(mount_point)

        # Create a service definitions and port mappings
        api_service = ecs.FargateService(
            self, 'APIService',
            cluster=cluster,
            task_definition=task_definition,
            desired_count=1,
            max_healthy_percent=500,
            min_healthy_percent=100,
            vpc_subnets=ec2.SubnetSelection(one_per_az=True, subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[ecs_security_group],
            service_connect_configuration=ecs.ServiceConnectProps(
                namespace=cloud_map_namespace.namespace_name,
                services=[ecs.ServiceConnectService(
                    port_mapping_name="api",  # Logical name for the service
                    port=8000,  # Container port
                )]),
            service_name="api-service")
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
        #web_app_service.service.connections.allow_from(file_system, ec2.Port.tcp(2049))
        api_service.connections.allow_from(file_system, ec2.Port.tcp(2049))

        # Allow the EFS to connect to the ECS Service
        #web_app_service.service.connections.allow_to(file_system, ec2.Port.tcp(2049))
        api_service.connections.allow_to(file_system, ec2.Port.tcp(2049))

        target_group = elbv2.ApplicationTargetGroup(
            self, "APITargetGroup",
            target_group_name="api-target-group",
            vpc=vpc,
            port=8000,
            targets=[api_service],
            #targets=[web_app_service.service],
            target_type=elbv2.TargetType.IP,
            protocol=elbv2.ApplicationProtocol.HTTP,
            health_check=elbv2.HealthCheck(
                path="/docs",
                port="8000",
                interval=Duration.seconds(60),
                timeout=Duration.seconds(5),
                healthy_threshold_count=2,
                unhealthy_threshold_count=2,
            ),
        )
        target_group.set_attribute(key="deregistration_delay.timeout_seconds",
                                   value="120")

        lb_rule = elbv2.ApplicationListenerRule(
            self, "APIListenerRule",
            listener=api_listener,
            priority=2,
            action=elbv2.ListenerAction.forward(target_groups=[target_group]),
            conditions=[elbv2.ListenerCondition.path_patterns(["*"])],
        )
