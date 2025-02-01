#!/usr/bin/env python3

import aws_cdk as cdk

from cqc_lem.aws.cdk.ecs.fargate_service.api_stack import APIStack
from cqc_lem.aws.cdk.ecs.fargate_service.web_stack import WebStack
from cqc_lem.aws.cdk.main_stack import MainStack
from cqc_lem.aws.util import get_cdk_env

app = cdk.App()
env = get_cdk_env()

main_stack = MainStack(app, "CQC-LEM", env=env)

web_stack = WebStack(app, "WebStack",
                     env=env,
                     vpc=main_stack.vpc,
                     cluster=main_stack.ecs_stack.ecs_cluster,
                     ecs_security_group=main_stack.ecs_stack.ECSSecurityGroup,
                     cloud_map_namespace=main_stack.ecs_stack.default_cloud_map_namespace,
                     # ecs_task_iam_role=main_stack.ECSTaskIamRole,
                     task_execution_role=main_stack.TaskExecutionRole,
                     repository_image_asset=main_stack.ecr_stack.docker_asset,
                     myql_secret_name=main_stack.mysql_stack.myql_secret_name,
                     efs_volume_name=main_stack.efs_stack.efs_volume_name,
                     efs_volume_configuration=main_stack.efs_stack.efs_volume_configuration,
                     mount_point=main_stack.efs_stack.mount_point,
                     web_listener=main_stack.ecs_stack.web_listener,
                     file_system=main_stack.efs_stack.file_system,
                     )

# Add dependencies to ensure correct order
web_stack.add_dependency(main_stack)

api_stack = APIStack(app, "APIStack",
                     env=env,
                     vpc=main_stack.vpc,
                     cluster=main_stack.ecs_stack.ecs_cluster,
                     ecs_security_group=main_stack.ecs_stack.ECSSecurityGroup,
                     cloud_map_namespace=main_stack.ecs_stack.default_cloud_map_namespace,
                     # ecs_task_iam_role=main_stack.ECSTaskIamRole,
                     task_execution_role=main_stack.TaskExecutionRole,
                     repository_image_asset=main_stack.ecr_stack.docker_asset,
                     myql_secret_name=main_stack.mysql_stack.myql_secret_name,
                     efs_volume_name=main_stack.efs_stack.efs_volume_name,
                     efs_volume_configuration=main_stack.efs_stack.efs_volume_configuration,
                     mount_point=main_stack.efs_stack.mount_point,
                     api_listener=main_stack.ecs_stack.api_listener,
                     file_system=main_stack.efs_stack.file_system,
                     )

# Add dependencies to ensure correct order
api_stack.add_dependency(main_stack)

'''



api_stack = APIStack(app, "APIStack", env=env,
                     vpc=main_stack.vpc,
                     cluster=main_stack.ecs_stack.ecs_cluster,
                     ecs_security_group=main_stack.ecs_stack.ECSSecurityGroup,
                     cloud_map_namespace=main_stack.ecs_stack.default_cloud_map_namespace,
                     ecs_task_iam_role=main_stack.ECSTaskIamRole,
                     task_execution_role=main_stack.TaskExecutionRole,
                     repository_image_asset=main_stack.ecr_stack.docker_asset,
                     mysql_host=main_stack.mysql_stack.db_instance_endpoint_address,
                     efs_volume_name=main_stack.efs_stack.efs_volume_name,
                     efs_volume_configuration=main_stack.efs_stack.efs_volume_configuration,
                     mount_point=main_stack.efs_stack.mount_point)

# Add dependencies to ensure correct order
api_stack.add_dependency(main_stack)

celery_queue_stack = CeleryQueueStack(app, "CeleryQueueStack", env=env, vpc=main_stack.vpc)
# Add dependencies to ensure correct order
celery_queue_stack.add_dependency(main_stack)

celery_worker_stack = CeleryWorkerStack(app, "CeleryWorkerStack", env=env,
                                        vpc=main_stack.vpc,
                                        task_execution_role=main_stack.TaskExecutionRole,
                                        repository_image_asset=main_stack.ecr_stack.docker_asset,
                                        mysql_host=main_stack.mysql_stack.db_instance_endpoint_address,
                                        queue_url=celery_queue_stack.queue_url,
                                        redis_url=celery_queue_stack.redis_url,
                                        file_system=main_stack.efs_stack.file_system,
                                        efs_app_assets_path=main_stack.efs_stack.efs_app_assets_path,
                                        access_point=main_stack.efs_stack.access_point,
                                        efs_task_role=main_stack.ECSTaskIamRole)
# Add dependencies to ensure correct order
celery_worker_stack.add_dependency(main_stack)
celery_worker_stack.add_dependency(celery_queue_stack)

celery_flower_stack = CeleryFlowerStack(app, "CeleryFlowerStack", env=env,
                                        vpc=main_stack.vpc,
                                        cluster=main_stack.ecs_stack.ecs_cluster,
                                        ecs_security_group=main_stack.ecs_stack.ECSSecurityGroup,
                                        cloud_map_namespace=main_stack.ecs_stack.default_cloud_map_namespace,
                                        ecs_task_iam_role=main_stack.ECSTaskIamRole,
                                        task_execution_role=main_stack.TaskExecutionRole,
                                        repository_image_asset=main_stack.ecr_stack.docker_asset,
                                        efs_volume_name=main_stack.efs_stack.efs_volume_name,
                                        efs_volume_configuration=main_stack.efs_stack.efs_volume_configuration,
                                        mount_point=main_stack.efs_stack.mount_point,
                                        queue_url=celery_queue_stack.queue_url,
                                        redis_url=celery_queue_stack.redis_url)

# Add dependencies to ensure correct order
celery_flower_stack.add_dependency(main_stack)
celery_flower_stack.add_dependency(celery_queue_stack)
'''

app.synth()
