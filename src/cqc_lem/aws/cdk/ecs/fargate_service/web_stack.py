from aws_cdk import (
    Duration,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_ecr_assets as ecr_assets,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ec2 as ec2, NestedStack, )
from constructs import Construct


class WebStack(NestedStack):

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
                 mysql_host: str,
                 efs_volume_name: str,
                 efs_volume_configuration: ecs.EfsVolumeConfiguration,
                 mount_point: ecs.MountPoint,
                 **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a new Fargate Task Definition
        task_definition = ecs.FargateTaskDefinition(
            self, 'WebFargateTaskDef',
            family='web_app',
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
        web_app_container = task_definition.add_container("WebAppContainer",
                                                          container_name="web_app",
                                                          image=ecs.ContainerImage.from_docker_image_asset(
                                                              repository_image_asset),
                                                          command=["/start"],  # Custom command
                                                          environment={
                                                              "MYSQL_HOST": mysql_host,
                                                              "MYSQL_PORT": "3306",
                                                              "MYSQL_USER": "user",
                                                              # TODO: Take this out so it uses AWS Secret
                                                              "MYSQL_PASSWORD": "password",
                                                              # TODO: Take this out so it uses AWS Secret
                                                              "AWS_SECRET_NAME": "admin",
                                                              # TODO: Put this back so it uses AWS Secret
                                                              "STREAMLIT_EMAIL": "christopher.queen@gmail.com",
                                                              "STREAMLIT_PORT": "8501",
                                                          },
                                                          port_mappings=[
                                                              ecs.PortMapping(
                                                                  container_port=8501,
                                                                  host_port=8501,
                                                                  name="web_app"  # Name of the port mapping
                                                              )
                                                          ],
                                                          logging=ecs.LogDriver.aws_logs(stream_prefix="web-app-logs"))

        # Add a new volume to the Fargate Task Definition
        web_app_container.add_mount_points(mount_point)

        # Create a service definitions and port mappings
        web_app_service = ecs.FargateService(
            self, 'WebAppService',
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
                    port_mapping_name="web_app",  # Logical name for the service
                    port=8501,  # Container port
                )]),
            service_name="web-app-service")


        # TODO: Figure out this auto scaling
        # Create a new Auto Scaling Policy for the ECS Service
        '''scalable_target = web_app_service.service.auto_scale_task_count(
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
            self, "WebAppTargetGroup",
            target_group_name="web-app-target-group",
            vpc=vpc,
            port=80,
            targets=[web_app_service],
            target_type=elbv2.TargetType.IP,
            protocol=elbv2.ApplicationProtocol.HTTP,
            health_check=elbv2.HealthCheck(
                path="/",
                port="8501",
                interval=Duration.seconds(6),
                timeout=Duration.seconds(5),
                healthy_threshold_count=2,
                unhealthy_threshold_count=2,
            ),
        )
        target_group.set_attribute(key="deregistration_delay.timeout_seconds",
                                   value="120")
        public_lb_sg.add_ingress_rule(peer=ec2.Peer.any_ipv4(), connection=ec2.Port.tcp(80),
                                      description="Allow HTTP traffic")

        listener = public_lb.add_listener("WebAppListener", port=80,
                                          default_action=elbv2.ListenerAction.forward(target_groups=[target_group]))

        lb_rule = elbv2.ApplicationListenerRule(
            self, "WebAppListenerRule",
            listener=listener,
            priority=1,
            action=elbv2.ListenerAction.forward(target_groups=[target_group]),
            conditions=[elbv2.ListenerCondition.path_patterns(["*"])],
        )
