import aws_cdk as core
import aws_cdk.assertions as assertions

from cqc_lem.aws.cdk.main_stack import MainStack


def test_main_stack_created():
    app = core.App()
    stack = MainStack(app, "MainStack-Test")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
