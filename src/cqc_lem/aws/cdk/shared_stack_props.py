from aws_cdk import (
    StackProps,
    aws_ecs as ecs,
    aws_efs as efs,
    aws_iam as iam,
    aws_logs as logs,
    aws_lambda as _lambda,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ec2 as ec2, Environment, )
from aws_cdk.aws_ecr_assets import DockerImageAsset
from aws_cdk.aws_lambda import IFunction
from aws_cdk.aws_servicediscovery import INamespace


class SharedStackProps(StackProps):
    props: dict = {}

    def __init__(self,

                 ec2_vpc: ec2.Vpc = None,
                 ecr_docker_asset: DockerImageAsset = None,
                 rds_db_instance_endpoint_address: str = None,
                 ssm_myql_secret_name: str = None,
                 efs_file_system: efs.FileSystem = None,
                 efs_access_point: efs.AccessPoint = None,
                 efs_volume_configuration: ecs.EfsVolumeConfiguration = None,
                 efs_task_role: iam.Role = None,
                 efs_volume_name: str = None,
                 efs_app_assets_path: str = None,
                 ecs_mount_point: ecs.MountPoint = None,
                 ecs_task_iam_role: iam.Role = None,
                 task_execution_role: iam.Role = None,
                 ecs_cluster: ecs.Cluster = None,
                 ecs_default_cloud_map_namespace: INamespace = None,
                 ecs_service_log_group: logs.LogGroup = None,
                 ecs_security_group: ec2.SecurityGroup = None,
                 ec2_public_lb_sg: ec2.SecurityGroup = None,
                 elbv2_public_lb: elbv2.ApplicationLoadBalancer = None,
                 elbv2_web_listener: elbv2.ApplicationListener = None,
                 elbv2_api_listener: elbv2.ApplicationListener = None,
                 elbv2_flower_listener: elbv2.ApplicationListener = None,
                 sqs_queue_url: str = None,
                 redis_url: str = None,
                 env: Environment = None,
                 lambda_get_redis_queue_message_count: IFunction = None,
                 celery_worker_log_group_arn: str = None,

                 **kwargs):
        super().__init__(env=env)
        self.props = kwargs
        self.props['env'] = env
        self.props['ec2_vpc'] = ec2_vpc
        self.props['ecr_docker_asset'] = ecr_docker_asset
        self.props['rds_db_instance_endpoint_address'] = rds_db_instance_endpoint_address
        self.props['ssm_myql_secret_name'] = ssm_myql_secret_name
        self.props['efs_file_system'] = efs_file_system
        self.props['efs_access_point'] = efs_access_point
        self.props['efs_volume_configuration'] = efs_volume_configuration
        self.props['efs_task_role'] = efs_task_role
        self.props['efs_volume_name'] = efs_volume_name
        self.props['efs_app_assets_path'] = efs_app_assets_path
        self.props['ecs_mount_point'] = ecs_mount_point
        self.props['ecs_task_iam_role'] = ecs_task_iam_role
        self.props['task_execution_role'] = task_execution_role
        self.props['ecs_cluster'] = ecs_cluster
        self.props['ecs_default_cloud_map_namespace'] = ecs_default_cloud_map_namespace
        self.props['ecs_service_log_group'] = ecs_service_log_group
        self.props['ecs_security_group'] = ecs_security_group
        self.props['ec2_public_lb_sg'] = ec2_public_lb_sg
        self.props['elbv2_public_lb'] = elbv2_public_lb
        self.props['elbv2_web_listener'] = elbv2_web_listener
        self.props['elbv2_api_listener'] = elbv2_api_listener
        self.props['elbv2_flower_listener'] = elbv2_flower_listener
        self.props['sqs_queue_url'] = sqs_queue_url
        self.props['redis_url'] = redis_url
        self.props['lambda_get_redis_queue_message_count'] = lambda_get_redis_queue_message_count
        self.props['celery_worker_log_group_arn'] = celery_worker_log_group_arn

    def get(self, key):
        return self.props.get(key)

    def set(self, key, value):
        self.props[key] = value

    @property
    def env(self) -> Environment:
        return self.get('env')

    @property
    def ec2_vpc(self) -> ec2.Vpc:
        return self.get('ec2_vpc')

    @property
    def ecr_docker_asset(self) -> DockerImageAsset:
        return self.get('ecr_docker_asset')

    @property
    def rds_db_instance_endpoint_address(self) -> str:
        return self.get('rds_db_instance_endpoint_address')

    @property
    def ssm_myql_secret_name(self) -> str:
        return self.get('ssm_myql_secret_name')

    @property
    def efs_file_system(self) -> efs.FileSystem:
        return self.get('efs_file_system')

    @property
    def efs_access_point(self) -> efs.AccessPoint:
        return self.get('efs_access_point')

    @property
    def efs_volume_configuration(self) -> ecs.EfsVolumeConfiguration:
        return self.get('efs_volume_configuration')

    @property
    def efs_task_role(self) -> iam.Role:
        return self.get('efs_task_role')

    @property
    def efs_volume_name(self) -> str:
        return self.get('efs_volume_name')

    @property
    def efs_app_assets_path(self) -> str:
        return self.get('efs_app_assets_path')

    @property
    def ecs_mount_point(self) -> ecs.MountPoint:
        return self.get('ecs_mount_point')

    @property
    def ecs_task_iam_role(self) -> iam.Role:
        return self.get('ecs_task_iam_role')

    @property
    def task_execution_role(self) -> iam.Role:
        return self.get('task_execution_role')

    @property
    def ecs_cluster(self) -> ecs.Cluster:
        return self.get('ecs_cluster')

    @property
    def ecs_default_cloud_map_namespace(self) -> INamespace:
        return self.get('ecs_default_cloud_map_namespace')

    @property
    def ecs_service_log_group(self) -> logs.LogGroup:
        return self.get('ecs_service_log_group')

    @property
    def ecs_security_group(self) -> ec2.SecurityGroup:
        return self.get('ecs_security_group')

    @property
    def public_lb_sg(self) -> ec2.SecurityGroup:
        return self.get('public_lb_sg')

    @property
    def ec2_public_lb_sg(self) -> elbv2.ApplicationLoadBalancer:
        return self.get('ec2_public_lb_sg')

    @property
    def elbv2_public_lb(self) -> elbv2.ApplicationLoadBalancer:
        return self.get('elbv2_public_lb')

    @property
    def elbv2_web_listener(self) -> elbv2.ApplicationListener:
        return self.get('elbv2_web_listener')

    @property
    def elbv2_api_listener(self) -> elbv2.ApplicationListener:
        return self.get('elbv2_api_listener')

    @property
    def elbv2_flower_listener(self) -> elbv2.ApplicationListener:
        return self.get('elbv2_flower_listener')

    @property
    def sqs_queue_url(self) -> str:
        return self.get('sqs_queue_url')

    @property
    def redis_url(self) -> str:
        return self.get('redis_url')

    @property
    def lambda_get_redis_queue_message_count(self) -> IFunction:
        return self.get('lambda_get_redis_queue_message_count')

    @property
    def celery_worker_log_group_arn(self) -> str:
        return self.get('celery_worker_log_group_arn')
