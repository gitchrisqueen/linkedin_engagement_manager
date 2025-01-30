#!/usr/bin/env python3

import aws_cdk as cdk
from cqc_lem.aws.cdk.main_stack import MainStack

app = cdk.App()
main_stack = MainStack(app, "CQC-LEM")

app.synth()
