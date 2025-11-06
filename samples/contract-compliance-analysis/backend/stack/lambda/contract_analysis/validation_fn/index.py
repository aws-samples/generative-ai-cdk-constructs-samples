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
import boto3
from aws_lambda_powertools import Logger

logger = Logger(service="contract-compliance-analysis")


@logger.inject_lambda_context(log_event=True)
def handler(event, context):
    """Lambda to validate contract type exists and is active"""
    contract_type_id = event.get("ContractTypeId")

    if not contract_type_id:
        logger.error("ContractTypeId not provided in event")
        raise ValueError("ContractTypeId is required")

    logger.info("Validating contract type", extra={"contract_type_id": contract_type_id})

    # Initialize DynamoDB table inside handler
    dynamodb = boto3.resource('dynamodb')
    contract_types_table = dynamodb.Table(os.environ['CONTRACT_TYPES_TABLE'])

    try:
        # Get contract type from DynamoDB
        response = contract_types_table.get_item(
            Key={'contract_type_id': contract_type_id}
        )

        if 'Item' not in response:
            logger.error("Contract type not found", extra={"contract_type_id": contract_type_id})
            raise ValueError(f"Contract type '{contract_type_id}' not found")

        contract_type = response['Item']

        if not contract_type.get('is_active', False):
            logger.error("Contract type is not active", extra={"contract_type_id": contract_type_id})
            raise ValueError(f"Contract type '{contract_type_id}' is not active")

        logger.info("Contract type validation successful", extra={
            "contract_type_id": contract_type_id,
            "contract_type_name": contract_type.get('name', 'unknown')
        })

        # Return the original event to pass through to next step
        return event

    except Exception as e:
        logger.error("Contract type validation failed", extra={
            "contract_type_id": contract_type_id,
            "error": str(e)
        })
        raise