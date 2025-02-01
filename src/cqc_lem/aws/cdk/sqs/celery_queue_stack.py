from aws_cdk import (
    aws_elasticache as elasticache,
    aws_sqs as sqs,
    aws_ec2 as ec2, CfnOutput, Stack, )
from constructs import Construct


class CeleryQueueStack(Stack):

    def __init__(self, scope: Construct, id: str, vpc: ec2.Vpc,
                 **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create SQS queue
        queue = sqs.Queue(self, "CeleryQueue")

        self.queue_url = queue.queue_url

        # Create a new subnet group for the Redis cluster
        redis_subnet_group = elasticache.CfnSubnetGroup(self, "RedisSubnetGroup",
                                                        description="Subnet group for Redis cluster",
                                                        subnet_ids=vpc.select_subnets(
                                                            subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS).subnet_ids
                                                        )

        # Create Elastic Cache Redis Cluster
        redis_cluster = elasticache.CfnCacheCluster(self, "RedisCluster",
                                                    cache_node_type="cache.t2.micro",
                                                    engine="redis",
                                                    num_cache_nodes=1,
                                                    vpc_security_group_ids=[vpc.vpc_default_security_group],
                                                    cache_subnet_group_name=redis_subnet_group.ref
                                                    )

        self.redis_url = redis_cluster.attr_redis_endpoint_address

        # Output resources
        CfnOutput(self, "RedisEndpointAddress", export_name="RedisEndpointAddress", value=self.redis_url)
        CfnOutput(self, "CeleryQueueUrl", export_name="CeleryQueueUrl", value=self.queue_url)
