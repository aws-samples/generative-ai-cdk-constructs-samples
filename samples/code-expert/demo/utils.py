#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import json

import boto3

from args import Args

stepfunction_client = boto3.client("stepfunctions")
s3_client = boto3.client("s3")
s3_resource = boto3.resource("s3")


def upload_file_to_s3(name, file_bytes):
    key = f"dataset/{name}.zip"
    s3_client.put_object(Body=file_bytes, Bucket=Args.s3_bucket, Key=key)
    return key


def get_object_from_s3(bucket, key):
    content_object = s3_resource.Object(bucket, key)
    return content_object.get()["Body"].read().decode("utf-8")


def start_step_functions_execution(name, execution_input):
    result = stepfunction_client.start_execution(
        name=name, stateMachineArn=Args.stepfunctions_arn, input=json.dumps(execution_input)
    )
    return result["executionArn"]


def get_step_functions_executions():
    return stepfunction_client.list_executions(stateMachineArn=Args.stepfunctions_arn)


def get_step_functions_execution_details(execution_arn):
    return stepfunction_client.describe_execution(executionArn=execution_arn)
