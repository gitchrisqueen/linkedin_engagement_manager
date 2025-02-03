from aws_cdk import (
    Stack,
    aws_logs as logs,
    aws_iam as iam,
    aws_ec2 as ec2, CfnOutput, RemovalPolicy, )
from constructs import Construct

from cqc_lem.aws.cdk.ecr.ecr_stack import EcrStack
from cqc_lem.aws.cdk.ecs.ecs_stack import EcsStack
from cqc_lem.aws.cdk.efs.efs_stack import EFSStack
from cqc_lem.aws.cdk.elasticcache.redis_stack import RedisStack
from cqc_lem.aws.cdk.lambda_stack import LambdaStack
from cqc_lem.aws.cdk.rds.mysql_stack import MySQLStack
from cqc_lem.aws.cdk.shared_stack_props import SharedStackProps


class MainStack(Stack):

    def __init__(self, scope: Construct, id: str,
                 props: SharedStackProps,
                 **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Creating a shared VPC with public subnets and private subnets with NAT Gateways
        vpc = ec2.Vpc(self, "Vpc",
                      ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
                      create_internet_gateway=True,
                      max_azs=2,
                      nat_gateways=2,
                      enable_dns_hostnames=True,
                      enable_dns_support=True,
                      vpc_name="CQC LEM VPC",
                      subnet_configuration=[
                          ec2.SubnetConfiguration(
                              subnet_type=ec2.SubnetType.PUBLIC,
                              name="Public",
                              cidr_mask=24
                          ),
                          ec2.SubnetConfiguration(
                              subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                              name="Private",
                              cidr_mask=24
                          )
                      ]
                      )

        # AWSRegion = Stack.of(self).region
        # AWSStackId = Stack.of(self).stack_id


        mysql_stack = MySQLStack(self, "MySQLStack", vpc=vpc)
        redis_stack = RedisStack(self, "RedisStack", vpc=vpc)
        lambda_stack = LambdaStack(self, "LambdaStack",
                                   vpc=vpc, redis_url=redis_stack.redis_url)
        lambda_stack.add_dependency(redis_stack)

        efs_stack = EFSStack(self, "EFSStack", vpc=vpc)
        ecs_stack = EcsStack(self, "EcsStack", vpc=vpc)

        API_BASE_URL_BUILD_ARG =  f"http://{ecs_stack.public_lb.load_balancer_dns_name}:8000"
        ecr_stack = EcrStack(self, "EcrStack", API_BASE_URL_BUILD_ARG=API_BASE_URL_BUILD_ARG)



        celery_worker_log_group = logs.LogGroup(
            self, "CeleryWorkerLogGroup",
            log_group_name="/cqc-lem/celery_worker",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )


        # Creating the task and execution IAM roles that the containers will assume to read and write to cloudwatch, Task Execution
        # Role will read from ECR
        ECSTaskIamRole = iam.Role(self, "ECSTaskIamRole",
                                  assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
                                  managed_policies=[
                                      iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchFullAccess"),
                                  ],
                                  )
        TaskExecutionRole = iam.Role(self, "TaskExecutionRole",
                                     assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com").with_conditions({
                                         "StringEquals": {
                                             "aws:SourceAccount": Stack.of(self).account
                                         },
                                         "ArnLike": {
                                             "aws:SourceArn": "arn:aws:ecs:" + Stack.of(
                                                 self).region + ":" + Stack.of(self).account + ":*"
                                         },
                                     }),
                                     managed_policies=[
                                         iam.ManagedPolicy.from_aws_managed_policy_name(
                                             "service-role/AmazonECSTaskExecutionRolePolicy"),
                                         iam.ManagedPolicy.from_aws_managed_policy_name(
                                             "AmazonEC2ContainerRegistryReadOnly"),
                                         iam.ManagedPolicy.from_aws_managed_policy_name(
                                             "CloudWatchLogsFullAccess"),
                                     ],
                                     )

        # Attach a managed policy to the IAM Role
        TaskExecutionRole.attach_inline_policy(
            iam.Policy(self, 'TaskExecEFSPolicy',
                       statements=[
                           iam.PolicyStatement(
                               effect=iam.Effect.ALLOW,
                               resources=['*'],
                               actions=[
                                   "ecr:GetAuthorizationToken",
                                   "ec2:DescribeAvailabilityZones"
                               ]
                           ),
                           iam.PolicyStatement(
                               sid='AllowEfsAccess',
                               effect=iam.Effect.ALLOW,
                               resources=['*'],
                               actions=[
                                   'elasticfilesystem:ClientRootAccess',
                                   'elasticfilesystem:ClientWrite',
                                   'elasticfilesystem:ClientMount',
                                   'elasticfilesystem:DescribeMountTargets'
                               ]
                           )
                       ]
                       )
        )

        # Output resources
        CfnOutput(self, "VPC", value=vpc.vpc_id)
        CfnOutput(self, "LoadBalancerArn", value=ecs_stack.public_lb.load_balancer_arn)
        CfnOutput(self, "LoadBalancerSGID", value=ecs_stack.public_lb_sg.security_group_id)

        # Prepares output attributes to be passed into other stacks
        self.output_props = props.props.copy()
        self.output_props['ec2_vpc'] = vpc
        self.output_props['ecr_docker_asset'] = ecr_stack.docker_asset
        self.output_props['rds_db_instance_endpoint_address'] = mysql_stack.db_instance_endpoint_address
        self.output_props['ssm_myql_secret_name'] = mysql_stack.myql_secret_name
        self.output_props['efs_file_system'] = efs_stack.file_system
        self.output_props['efs_access_point'] = efs_stack.efs_access_point
        self.output_props['efs_volume_configuration'] = efs_stack.efs_volume_configuration
        self.output_props['efs_task_role'] = efs_stack.EFSTaskRole
        self.output_props['efs_volume_name'] = efs_stack.efs_volume_name
        self.output_props['efs_app_assets_path'] = efs_stack.efs_app_assets_path
        self.output_props['ecs_mount_point'] = efs_stack.mount_point
        self.output_props['ecs_task_iam_role'] = ECSTaskIamRole
        self.output_props['task_execution_role'] = TaskExecutionRole
        self.output_props['ecs_cluster'] = ecs_stack.ecs_cluster
        self.output_props['ecs_default_cloud_map_namespace'] = ecs_stack.default_cloud_map_namespace
        self.output_props['ecs_service_log_group'] = ecs_stack.ecs_service_log_group
        self.output_props['ecs_security_group'] = ecs_stack.ecs_security_group
        self.output_props['ec2_public_lb_sg'] = ecs_stack.public_lb_sg
        self.output_props['elbv2_public_lb'] = ecs_stack.public_lb
        self.output_props['elbv2_web_listener'] = ecs_stack.web_listener
        self.output_props['elbv2_api_listener'] = ecs_stack.api_listener
        self.output_props['elbv2_flower_listener'] = ecs_stack.flower_listener
        self.output_props['redis_url'] = redis_stack.redis_url
        self.output_props['lambda_get_redis_queue_message_count'] = lambda_stack.get_queue_message_count
        self.output_props['celery_worker_log_group_arn'] = celery_worker_log_group.log_group_arn

    @property
    def outputs(self) -> SharedStackProps:
        return SharedStackProps(**self.output_props)
