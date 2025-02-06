from aws_cdk import (
    aws_rds as rds,
    aws_ecs as ecs,
    aws_ec2 as ec2, RemovalPolicy, CfnOutput, NestedStack, )
from constructs import Construct


class MySQLStack(NestedStack):
    vpc: ec2.Vpc = None
    cluster: ecs.Cluster = None

    def __init__(self, scope: Construct, id: str, vpc: ec2.Vpc, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create RDS MySQL Database
        db_instance = rds.DatabaseInstance(self, "MySQLDatabase",
                                           engine=rds.DatabaseInstanceEngine.mysql(
                                               version=rds.MysqlEngineVersion.VER_8_0_40
                                           ),
                                           vpc=vpc,
                                           # vpc_subnets makes this public to the web
                                           vpc_subnets=ec2.SubnetSelection(
                                               subnet_type=ec2.SubnetType.PUBLIC,
                                           ),
                                           allocated_storage=20,
                                           max_allocated_storage=100,
                                           multi_az=False,
                                           port=3306,
                                           instance_type=ec2.InstanceType.of(
                                               ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO
                                           ),
                                           # credentials=rds.Credentials.from_generated_secret("admin"),  # Optional - will default to 'admin' username and generated password
                                           database_name="linkedin_manager",
                                           removal_policy=RemovalPolicy.DESTROY,
                                           deletion_protection=False
                                           )

        # Allow connections from any IP address to pot 3306
        db_instance.connections.allow_from_any_ipv4(
            ec2.Port.tcp(3306),
            description="Mysql port for connection"
        )

        self.db_instance_endpoint_address = db_instance.db_instance_endpoint_address
        self.myql_secret_name = db_instance.secret.secret_name

        # Output resources
        CfnOutput(self, "DBInstanceEndpoint", value=db_instance.db_instance_endpoint_address)
        #CfnOutput(self, "DBSecretName", value=db_instance.secret.secret_name)
        #CfnOutput(self, "DBInstanceARN", value=db_instance.instance_arn)
