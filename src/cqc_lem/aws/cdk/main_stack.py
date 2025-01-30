from aws_cdk import (
    Stack,
    aws_ec2 as ec2, CfnOutput, )
from constructs import Construct

from cqc_lem.aws.cdk.batch.celery_stack import CeleryStack
from cqc_lem.aws.cdk.ecr.ecr_stack import EcrStack
from cqc_lem.aws.cdk.ecs.ecs_stack import EcsStack
from cqc_lem.aws.cdk.ecs.fargate_service.api_stack import APIStack
from cqc_lem.aws.cdk.ecs.fargate_service.celery_flower_stack import CeleryFlowerStack
from cqc_lem.aws.cdk.ecs.fargate_service.web_stack import WebStack
from cqc_lem.aws.cdk.efs.efs_stack import EFSStack
from cqc_lem.aws.cdk.rds.mysql_stack import MySQLStack


class MainStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
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

        AWSRegion = Stack.of(self).region
        AWSStackId = Stack.of(self).stack_id
        mysql_stack = MySQLStack(self, "MySQLStack", vpc=vpc)
        ecr_stack = EcrStack(self, "EcrStack")
        efs_stack = EFSStack(self, "EFSStack", vpc=vpc)
        ecs_stack = EcsStack(self, "EcsStack", vpc=vpc, repository=ecr_stack.docker_asset)
        web_stack = WebStack(self, "WebStack", vpc=vpc, cluster=ecs_stack.ecs_cluster,
                             public_lb_sg=ecs_stack.public_lb_sg,
                             public_lb=ecs_stack.public_lb, ecs_security_group=ecs_stack.ECSSecurityGroup,
                             cloud_map_namespace=ecs_stack.default_cloud_map_namespace,
                             ecs_task_iam_role=ecs_stack.ECSTaskIamRole,
                             task_execution_role=ecs_stack.TaskExecutionRole,
                             repository_image_asset=ecr_stack.docker_asset,
                             mysql_host=mysql_stack.db_instance_endpoint_address,
                             efs_volume_name=efs_stack.efs_volume_name,
                             efs_volume_configuration=efs_stack.efs_volume_configuration,
                             mount_point=efs_stack.mount_point)
        api_stack = APIStack(self, "APIStack", vpc=vpc, cluster=ecs_stack.ecs_cluster,
                             public_lb_sg=ecs_stack.public_lb_sg,
                             public_lb=ecs_stack.public_lb, ecs_security_group=ecs_stack.ECSSecurityGroup,
                             cloud_map_namespace=ecs_stack.default_cloud_map_namespace,
                             ecs_task_iam_role=ecs_stack.ECSTaskIamRole,
                             task_execution_role=ecs_stack.TaskExecutionRole,
                             repository_image_asset=ecr_stack.docker_asset,
                             mysql_host=mysql_stack.db_instance_endpoint_address,
                             efs_volume_name=efs_stack.efs_volume_name,
                             efs_volume_configuration=efs_stack.efs_volume_configuration,
                             mount_point=efs_stack.mount_point)
        celery_stack = CeleryStack(self, "CeleryStack", vpc=vpc,
                                   task_execution_role=ecs_stack.TaskExecutionRole,
                                   repository_image_asset=ecr_stack.docker_asset,
                                   mysql_host=mysql_stack.db_instance_endpoint_address,
                                   file_system=efs_stack.file_system,
                                   efs_app_assets_path=efs_stack.efs_app_assets_path,
                                   access_point=efs_stack.access_point,
                                   EFSTaskRole=ecs_stack.TaskExecutionRole)

        celery_flower_stack = CeleryFlowerStack(self, "CeleryFlowerStack", vpc=vpc, cluster=ecs_stack.ecs_cluster,
                                                public_lb_sg=ecs_stack.public_lb_sg, public_lb=ecs_stack.public_lb,
                                                ecs_security_group=ecs_stack.ECSSecurityGroup,
                                                cloud_map_namespace=ecs_stack.default_cloud_map_namespace,
                                                ecs_task_iam_role=ecs_stack.ECSTaskIamRole,
                                                task_execution_role=ecs_stack.TaskExecutionRole,
                                                repository_image_asset=ecr_stack.docker_asset,
                                                efs_volume_name=efs_stack.efs_volume_name,
                                                efs_volume_configuration=efs_stack.efs_volume_configuration,
                                                mount_point=efs_stack.mount_point,
                                                redis_endpoint_address=celery_stack.redis_url,
                                                queue_url=celery_stack.queue_url)

        # Output resources
        CfnOutput(self, "VPC", value=vpc.vpc_id)
