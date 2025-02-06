from aws_cdk import (
    Duration,
    aws_ecs as ecs,
    aws_logs as logs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ec2 as ec2, Stack, RemovalPolicy, )
from constructs import Construct

from cqc_lem.aws.cdk.shared_stack_props import SharedStackProps


class WebStack(Stack):

    def __init__(self, scope: Construct, id: str,
                 props: SharedStackProps,
                 **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a new Fargate Task Definition
        task_definition = ecs.FargateTaskDefinition(
            self, 'WebFargateTaskDef',
            family='web_app',
            cpu=512,
            memory_limit_mib=1024,
            task_role=props.task_execution_role

        )

        # Add a new volume to the Fargate Task Definition
        task_definition.add_volume(
            name=props.efs_volume_name,
            efs_volume_configuration=props.efs_volume_configuration,
        )

        # Add a new container to the Fargate Task Definition
        web_app_container = task_definition.add_container("WebAppContainer",
                                                          container_name="web_app",
                                                          image=ecs.ContainerImage.from_docker_image_asset(
                                                              props.ecr_docker_asset),
                                                          command=["/start-streamlit"],  # Custom command
                                                          environment={
                                                              "OPENAI_API_KEY": "Needs to come from secret",
                                                              # TODO: Need to get this ^^^ from file or AWS Secret
                                                              "AWS_MYSQL_SECRET_NAME": props.ssm_myql_secret_name,
                                                              "AWS_REGION": props.env.region,
                                                              "STREAMLIT_EMAIL": "christopher.queen@gmail.com",
                                                              "STREAMLIT_PORT": "8501",
                                                              "API_BASE_URL": props.api_base_url,
                                                              "API_PORT": "8000"
                                                          },
                                                          port_mappings=[
                                                              ecs.PortMapping(
                                                                  container_port=8501,
                                                                  host_port=8501,
                                                                  name="web_app"  # Name of the port mapping
                                                              )
                                                          ],
                                                          logging=ecs.LogDriver.aws_logs(
                                                              stream_prefix="web_app_logs",
                                                              log_group=logs.LogGroup(
                                                                  self, "WebApprLogGroup",
                                                                  log_group_name="/cqc-lem/web_app",
                                                                  retention=logs.RetentionDays.ONE_WEEK,
                                                                  removal_policy=RemovalPolicy.DESTROY
                                                              )
                                                          )
                                                          )

        # Add a new mount point to the Fargate Task Definition
        web_app_container.add_mount_points(props.ecs_asset_mount_point)

        # Create a service definitions and port mappings
        web_app_service = ecs.FargateService(
            self, 'WebAppService',
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
                    port_mapping_name="web_app",  # Logical name for the service
                    port=8501,  # Container port
                )]),
            service_name="web-app-service")
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
        web_app_service.connections.allow_from(props.efs_file_system, ec2.Port.tcp(2049))

        # Allow the EFS to connect to the ECS Service
        # web_app_service.service.connections.allow_to(file_system, ec2.Port.tcp(2049))
        web_app_service.connections.allow_to(props.efs_file_system, ec2.Port.tcp(2049))

        target_group = elbv2.ApplicationTargetGroup(
            self, "WebAppTargetGroup",
            target_group_name="web-app-target-group",
            vpc=props.ec2_vpc,
            port=8501,
            targets=[web_app_service],
            # targets=[web_app_service.service],
            target_type=elbv2.TargetType.IP,
            protocol=elbv2.ApplicationProtocol.HTTP,
            health_check=elbv2.HealthCheck(
                path="/",
                port="8501",
                interval=Duration.seconds(60),
                timeout=Duration.seconds(5),
                healthy_threshold_count=2,
                unhealthy_threshold_count=2,
            ),
        )
        target_group.set_attribute(key="deregistration_delay.timeout_seconds",
                                   value="120")

        lb_rule = elbv2.ApplicationListenerRule(
            self, "WebAppListenerRule",
            listener=props.elbv2_web_listener,
            priority=1,
            action=elbv2.ListenerAction.forward(target_groups=[target_group]),
            conditions=[elbv2.ListenerCondition.path_patterns(["*"])],
        )
