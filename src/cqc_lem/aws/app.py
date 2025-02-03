#!/usr/bin/env python3

import aws_cdk as cdk

from cqc_lem.aws.cdk.batch.celery_worker_stack import CeleryWorkerStack
from cqc_lem.aws.cdk.ecs.fargate_service.api_stack import APIStack
from cqc_lem.aws.cdk.ecs.fargate_service.celery_flower_stack import CeleryFlowerStack
from cqc_lem.aws.cdk.ecs.fargate_service.web_stack import WebStack
from cqc_lem.aws.cdk.main_stack import MainStack
from cqc_lem.aws.cdk.shared_stack_props import SharedStackProps
from cqc_lem.aws.util import get_cdk_env

app = cdk.App()
env = get_cdk_env()
props = SharedStackProps(env=env)

main_stack = MainStack(app, "CQC-LEM",
                       props=props,
                       env=env)

web_stack = WebStack(app, "WebStack",
                     env=env,
                     props=main_stack.outputs
                     )

# Add dependencies to ensure correct order
web_stack.add_dependency(main_stack)

api_stack = APIStack(app, "APIStack",
                     env=env,
                     props=main_stack.outputs
                     )

# Add dependencies to ensure correct order
api_stack.add_dependency(main_stack)

celery_worker_stack = CeleryWorkerStack(app, "CeleryWorkerStack",
                                        env=env,
                                        props=main_stack.outputs
                                        )

celery_worker_stack.add_dependency(main_stack)

celery_flower_stack = CeleryFlowerStack(app, "CeleryFlowerStack", env=env,
                                        props=main_stack.outputs)

celery_flower_stack.add_dependency(main_stack)

app.synth()
