#!/usr/bin/env python3
from os import (
    getenv,
)

from aws_cdk import (
    App, 
    Environment,
)

from llamaindex_lambda_loader.llamaindex_lambda_loader_stack import LlamaindexLambdaLoaderStack

app = App()
env = Environment(
    account=getenv('CDK_DEFAULT_ACCOUNT'), 
    region=getenv('CDK_DEFAULT_REGION'))

llamaindex = LlamaindexLambdaLoaderStack(
    scope=app,
    construct_id="LlamaindexLambdaLoaderStack" + getenv('SUFFIX',''),
    env=env,
)

app.synth()
