from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_ec2 as ec2, CfnOutput, )
from constructs import Construct

from cqc_lem.aws.cdk.ecr.ecr_stack import EcrStack
from cqc_lem.aws.cdk.ecs.ecs_stack import EcsStack
from cqc_lem.aws.cdk.efs.efs_stack import EFSStack
from cqc_lem.aws.cdk.rds.mysql_stack import MySQLStack


class MainStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Creating a shared VPC with public subnets and private subnets with NAT Gateways
        self.vpc = ec2.Vpc(self, "Vpc",
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

        self.ecr_stack = EcrStack(self, "EcrStack")
        self.mysql_stack = MySQLStack(self, "MySQLStack", vpc=self.vpc)
        self.efs_stack = EFSStack(self, "EFSStack", vpc=self.vpc)
        self.ecs_stack = EcsStack(self, "EcsStack", vpc=self.vpc)

        # Creating the task and execution IAM roles that the containers will assume to read and write to cloudwatch, Task Execution
        # Role will read from ECR
        self.ECSTaskIamRole = iam.Role(self, "ECSTaskIamRole",
                                       assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
                                       managed_policies=[
                                           iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchFullAccess"),
                                       ],
                                       )
        self.TaskExecutionRole = iam.Role(self, "TaskExecutionRole",
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
        self.TaskExecutionRole.attach_inline_policy(
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

        # Add tags to the load and security group balancer
        # items_to_tag = [self.ecs_stack.public_lb, self.ecs_stack.public_lb_sg]
        # for item in items_to_tag:
        #    Tags.of(item).add("Environment", AWS_ENV_TAG)
        #    Tags.of(item).add("Application", AWS_APPLICATION_TAG)

        # Create SSM parameters to store cross stack references
        # ssm.StringParameter(self, "LoadBalancerArn",
        #                    string_value=self.ecs_stack.public_lb.load_balancer_arn,
        #                    parameter_name="/CQC-LEM/LoadBalancerArn")
        # ssm.StringParameter(self, "LoadBalancerSGID",
        #                    string_value=self.ecs_stack.public_lb_sg.security_group_id,
        #                    parameter_name="/CQC-LEM/LoadBalancerSGID")

        # Output resources
        CfnOutput(self, "VPC", value=self.vpc.vpc_id)
        CfnOutput(self, "LoadBalancerArn", value=self.ecs_stack.public_lb.load_balancer_arn)
        CfnOutput(self, "LoadBalancerSGID", value=self.ecs_stack.public_lb_sg.security_group_id)
