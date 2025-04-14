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

from aws_cdk import (
    aws_dynamodb as dynamodb,
    RemovalPolicy,
)
from constructs import Construct

class TableConstruct(dynamodb.Table):
    """
    A construct that represents a DynamoDB table with specific configurations.

    This class extends the DynamoDB Table construct from AWS CDK and sets
    default properties such as billing mode, removal policy, point-in-time
    recovery, and encryption.

    Parameters:
    - scope (Construct): The scope in which this construct is defined.
    - construct_id (str): The unique identifier for this construct.
    - **kwargs: Additional properties to pass to the DynamoDB Table.
    """
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ):
        super().__init__(
            scope,
            construct_id,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            **kwargs,
        )