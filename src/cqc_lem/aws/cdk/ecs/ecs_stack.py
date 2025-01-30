from aws_cdk import (
    NestedStack,
    aws_ec2 as ec2,
    aws_servicediscovery as servicediscovery,
    aws_ecs as ecs,
    aws_logs as logs,
    aws_iam as iam,
    aws_ecr_assets as ecr_assets,
    aws_elasticloadbalancingv2 as elbv2,
    RemovalPolicy,
    CfnOutput

)
from constructs import Construct


class EcsStack(NestedStack):

    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.Vpc,
                 repository: ecr_assets.DockerImageAsset,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Creating the ECS Cluster and the cloud map namespace
        self.ecs_cluster = ecs.Cluster(self, "ECSCluster",
                                       vpc=vpc,
                                       cluster_name="CQC-LEM-Cluster",
                                       container_insights=True)
        self.default_cloud_map_namespace = self.ecs_cluster.add_default_cloud_map_namespace(name="cqc-lem.local",
                                                                                            use_for_service_connect=True,
                                                                                            type=servicediscovery.NamespaceType.DNS_PRIVATE)

        # Creating the Cloudwatch log group where ECS Logs will be stored
        self.ECSServiceLogGroup = logs.LogGroup(self, "ECSServiceLogGroup",
                                           log_group_name=f"{self.ecs_cluster.cluster_name}-service",
                                           removal_policy=RemovalPolicy.DESTROY,
                                           retention=logs.RetentionDays.ONE_WEEK,
                                           )

        # Creating the task and execution IAM roles that the containers will assume to read and write to cloudwatch, Task Execution
        # Role will read from ECR
        self.ECSTaskIamRole = iam.Role(self, "ECSTaskIamRole",
                                       assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
                                       managed_policies=[
                                           iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchFullAccess"),
                                       ],
                                       )
        self.TaskExecutionRole = iam.Role(self, "TaskExecutionRole",
                                          assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
                                          managed_policies=[
                                              iam.ManagedPolicy.from_aws_managed_policy_name(
                                                  "service-role/AmazonECSTaskExecutionRolePolicy"),
                                              iam.ManagedPolicy.from_aws_managed_policy_name(
                                                  "AmazonEC2ContainerRegistryReadOnly"),
                                              iam.ManagedPolicy.from_aws_managed_policy_name(
                                                  "CloudWatchLogsFullAccess"),
                                          ],
                                          )

        # ECS Security group, this will allow access from the Load Balancer and allow LAN access so that the
        # ECS containers can talk to each other on ingress ports
        self.ECSSecurityGroup = ec2.SecurityGroup(self, "ECSSecurityGroup",
                                                  vpc=vpc,
                                                  description="ECS Security Group",
                                                  allow_all_outbound=True,
                                                  )

        # TODO: Move below to API Fargate Stack
        self.ECSSecurityGroup.add_ingress_rule(ec2.Peer.ipv4(vpc.vpc_cidr_block), ec2.Port.tcp(8000),
                                               description="All traffic within VPC", )

        # Creating a public load balancer
        self.public_lb_sg = ec2.SecurityGroup(self, "PublicLBSG", vpc=vpc, description="Public LB SG",
                                              allow_all_outbound=True)

        self.public_lb = elbv2.ApplicationLoadBalancer(self, "FrontendLB", vpc=vpc, internet_facing=True,
                                                  security_group=self.public_lb_sg,
                                                  vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC))
        self.public_lb.set_attribute(key="idle_timeout.timeout_seconds", value="30")

        CfnOutput(self, "Load Balancer URL", value=f"http://{self.public_lb.load_balancer_dns_name}")
