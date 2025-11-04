#
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

import os
from typing import Any

from constructs import Construct
from aws_cdk import (
  Duration,
  aws_bedrockagentcore as bedrockagentcore,
  aws_dynamodb as dynamodb,
  aws_iam as iam,
  aws_lambda as lambda_,
  aws_lambda_python_alpha as python_lambda,
  aws_s3 as s3,
  aws_stepfunctions_tasks as tasks,
  Stack,
)
from cdk_nag import NagSuppressions, NagPackSuppression

import stack_constructs

LAMBDA_PATH = os.path.join(os.path.dirname(__file__), "check_legislation_agent_fn")
BOTO3_LAYER_PATH = os.path.join(os.path.dirname(__file__), "layers/boto3")

class CheckLegislationStep(Construct):
  """CDK construct for checking contract clauses against current legislation
  """

  def __init__(
      self,
      scope: Construct,
      id: str,
      agent_runtime: bedrockagentcore.CfnRuntime,
      agent_role: iam.IRole,
      clauses_table: dynamodb.ITable,
      contract_bucket: s3.IBucket,
      **kwargs: Any,
  ) -> None:
    super().__init__(scope, id, **kwargs)

    clauses_table.grant_read_write_data(agent_role)
    contract_bucket.grant_read(agent_role)

    agent_runtime_arn = agent_runtime.attr_agent_runtime_arn

    powertools_layer = lambda_.LayerVersion.from_layer_version_arn(self, "PowertoolsLayer",
                                                                   f"arn:aws:lambda:{Stack.of(self).region}:017000801446:layer:AWSLambdaPowertoolsPythonV3-python313-x86_64:21")

    boto3_layer = python_lambda.PythonLayerVersion(
      self, "Boto3PinnedLayer",
      entry=BOTO3_LAYER_PATH,  # folder containing requirements.txt
      compatible_runtimes=[lambda_.Runtime.PYTHON_3_13],
    )

    # Create the Lambda function for invoking AgentCore using PythonFunctionConstruct
    self.check_legislation_fn = stack_constructs.PythonFunctionConstruct(
      self,
      "CheckLegislationAgentFunction",
      entry=LAMBDA_PATH,
      index="index.py",
      handler="lambda_handler",
      runtime=lambda_.Runtime.PYTHON_3_13,
      architecture=lambda_.Architecture.X86_64,
      timeout=Duration.minutes(15),
      memory_size=512,
      environment={
        "LOG_LEVEL": "INFO",
        "AGENT_RUNTIME_ARN": agent_runtime_arn
      },
      layers=[boto3_layer, powertools_layer]
    )

    # Grant the Lambda function permission to invoke the AgentCore runtime
    self.check_legislation_fn.add_to_role_policy(
      iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=["bedrock-agentcore:InvokeAgentRuntime"],
        resources=[agent_runtime_arn, f"{agent_runtime_arn}/*"] if agent_runtime_arn != "*" else ["*"]
      )
    )

    # Create the Step Functions task to invoke the Lambda
    self.sfn_task = tasks.LambdaInvoke(
      self, "InvokeAgent",
      lambda_function=self.check_legislation_fn,
      payload_response_only=True,
      result_path="$.LegislationCheck",
    )

    # Add retry logic for Lambda errors
    self.sfn_task.add_retry(
      errors=['Lambda.ServiceException', 'Lambda.AWSLambdaException', 'Lambda.SdkClientException',
              'Lambda.ClientExecutionTimeoutException', 'Lambda.Unknown'],
      max_attempts=5,
      interval=Duration.seconds(2),
      backoff_rate=2.0
    )

    NagSuppressions.add_resource_suppressions(
      self.check_legislation_fn.role,  # type:ignore[arg-type]
      suppressions=[
        NagPackSuppression(
          id="AwsSolutions-IAM5",
          # applies_to=["Resource::arn:aws:bedrock-agentcore:<AWS::Region>:<AWS::AccountId>:runtime/*/*"],  # this is triggering for the agent's arn. Ideally we'd list it here, but it's defined after the agent is deployed
          reason="Needs to be able to call any version of the agent"
        )
      ],
      apply_to_children=True,
    )

    NagSuppressions.add_resource_suppressions(
      agent_role,  # type:ignore[arg-type]
      suppressions=[
        NagPackSuppression(
          id="AwsSolutions-IAM5",
          applies_to=[
            "Action::s3:GetObject*",
            "Action::s3:GetBucket*",
            "Action::s3:List*",
            "Resource::<ContractBucketFE738A79.Arn>/*",
          ],
          reason="Needs to be able to call any version of the agent"
        )
      ],
      apply_to_children=True,
    )
