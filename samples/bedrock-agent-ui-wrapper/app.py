
#!/usr/bin/env python3
import os
import aws_cdk as cdk
import yaml
from yaml.loader import SafeLoader
from cdk_nag import AwsSolutionsChecks

from infra.capsule_stack import CapsuleStack

with open(os.path.join(os.path.dirname(__file__), "config.yml"), encoding="utf-8") as f:
    stack_config = yaml.load(f, Loader=SafeLoader)

app = cdk.App()
env = cdk.Environment(account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION"))

CapsuleStack(scope=app, construct_id=stack_config["stack_name"], config=stack_config, env=env)
cdk.Aspects.of(app).add(AwsSolutionsChecks())

app.synth()
