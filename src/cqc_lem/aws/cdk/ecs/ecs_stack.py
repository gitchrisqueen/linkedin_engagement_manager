from aws_cdk import (
    NestedStack,
    aws_ec2 as ec2,
    aws_servicediscovery as servicediscovery,
    aws_ecs as ecs,
    aws_logs as logs,
    aws_elasticloadbalancingv2 as elbv2,
    RemovalPolicy,
    CfnOutput

)
from constructs import Construct


class EcsStack(NestedStack):

    def __init__(self, scope: Construct, id: str, vpc: ec2.Vpc,
                 **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Creating the ECS Cluster and the cloud map namespace
        self.ecs_cluster = ecs.Cluster(self, "ECSCluster",
                                       vpc=vpc,
                                       cluster_name="CQC-LEM-Cluster",
                                       container_insights=True)
        self.default_cloud_map_namespace = self.ecs_cluster.add_default_cloud_map_namespace(name="cqc-lem.local",
                                                                                            use_for_service_connect=True,
                                                                                            type=servicediscovery.NamespaceType.DNS_PRIVATE)

        # Creating the Cloudwatch log group where ECS Logs will be stored
        self.ecs_service_log_group = logs.LogGroup(self, "ECSServiceLogGroup",
                                                log_group_name=f"/cqc-lem/cluster_service",
                                                removal_policy=RemovalPolicy.DESTROY,
                                                retention=logs.RetentionDays.ONE_WEEK,
                                                )

        # ECS Security group, this will allow access from the Load Balancer and allow LAN access so that the
        # ECS containers can talk to each other on ingress ports
        self.ecs_security_group = ec2.SecurityGroup(self, "ECSSecurityGroup",
                                                  vpc=vpc,
                                                  description="ECS Security Group",
                                                  allow_all_outbound=True,
                                                  )

        # Security Group ingress rules for traffic among containers
        self.ecs_security_group.add_ingress_rule(ec2.Peer.ipv4(vpc.vpc_cidr_block), ec2.Port.tcp(8000),
                                               description="API traffic within VPC", )

        self.ecs_security_group.add_ingress_rule(ec2.Peer.ipv4(vpc.vpc_cidr_block), ec2.Port.tcp(8501),
                                               description="Web traffic within VPC", )

        self.ecs_security_group.add_ingress_rule(ec2.Peer.ipv4(vpc.vpc_cidr_block), ec2.Port.tcp(5555),
                                               description="Celery Flower traffic within VPC", )

        self.ecs_security_group.add_ingress_rule(ec2.Peer.ipv4(vpc.vpc_cidr_block), ec2.Port.tcp(6379),
                                                 description="Redis traffic within VPC", )

        self.ecs_security_group.add_ingress_rule(ec2.Peer.ipv4(vpc.vpc_cidr_block), ec2.Port.tcp(3306),
                                                 description="MySql traffic within VPC", )

        # Creating a public load balancer
        self.public_lb_sg = ec2.SecurityGroup(self, "PublicLBSG", vpc=vpc, description="Public LB SG",
                                              allow_all_outbound=True)

        self.public_lb = elbv2.ApplicationLoadBalancer(self, "FrontendLB", vpc=vpc, internet_facing=True,
                                                       security_group=self.public_lb_sg,
                                                       vpc_subnets=ec2.SubnetSelection(
                                                           subnet_type=ec2.SubnetType.PUBLIC))


        self.public_lb.set_attribute(key="idle_timeout.timeout_seconds", value="30")

        self.public_lb_sg.add_ingress_rule(peer=ec2.Peer.any_ipv4(), connection=ec2.Port.tcp(80),
                                           description="Allow Web App traffic")

        self.web_listener = self.public_lb.add_listener("WebAppListener", port=80,
                                                        default_action=elbv2.ListenerAction.fixed_response(
                                                            status_code=200,
                                                            content_type="text/plain",
                                                            message_body="OK"))

        self.public_lb_sg.add_ingress_rule(peer=ec2.Peer.any_ipv4(), connection=ec2.Port.tcp(8000),
                                           description="Allow API traffic")
        self.api_listener = self.public_lb.add_listener("APIListener", port=8000,
                                                        protocol=elbv2.ApplicationProtocol.HTTP,
                                                        default_action=elbv2.ListenerAction.fixed_response(
                                                            status_code=200,
                                                            content_type="text/plain",
                                                            message_body="OK"))

        self.public_lb_sg.add_ingress_rule(peer=ec2.Peer.any_ipv4(), connection=ec2.Port.tcp(5555),
                                           description="Allow Celery Flower traffic")
        self.flower_listener = self.public_lb.add_listener("CeleryFlowerListener", port=5555,
                                                           protocol=elbv2.ApplicationProtocol.HTTP,
                                                           default_action=elbv2.ListenerAction.fixed_response(
                                                               status_code=200,
                                                               content_type="text/plain",
                                                               message_body="OK"))

        CfnOutput(self, "Load Balancer URL", value=f"http://{self.public_lb.load_balancer_dns_name}")
