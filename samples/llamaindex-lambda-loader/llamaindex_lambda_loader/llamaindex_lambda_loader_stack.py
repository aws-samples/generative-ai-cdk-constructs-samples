#!/usr/bin/env python3

import os

from aws_cdk import (
    Duration,
    Stack,
    aws_lambda,
)
from constructs import Construct

from cdklabs.generative_ai_cdk_constructs import (
    LlamaindexCommonDepsLayer,   
)

from aws_cdk.aws_lambda_python_alpha import (
    # BundlingOptions,
    PythonFunction,
    # PythonLayerVersion
)

class LlamaindexLambdaLoaderStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # lambda_deps_layer = LlamaindexCommonDepsLayer(
        #     self,
        #     'LambdaLlamaIndexLayer',
        #     runtime=aws_lambda.Runtime.PYTHON_3_12,
        #     architecture=aws_lambda.Architecture.X86_64,
        #     auto_upgrade=True,
        # )
        
        lambda_function = PythonFunction(
            self,
            "LambdaFunction",
            runtime=aws_lambda.Runtime.PYTHON_3_10,
            architecture=aws_lambda.Architecture.X86_64,
            entry=os.path.join(os.path.dirname(__file__), './lambda/'),
            # layers=[
            #     lambda_deps_layer,
            #     # aws_lambda.LayerVersion.from_layer_version_arn(
            #     #     self,
            #     #     'PowerToolsLayer', 
            #     #     f'arn:aws:lambda:{self.region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:60'
            #     # )
            # ],
            timeout= Duration.minutes(2),
        )   