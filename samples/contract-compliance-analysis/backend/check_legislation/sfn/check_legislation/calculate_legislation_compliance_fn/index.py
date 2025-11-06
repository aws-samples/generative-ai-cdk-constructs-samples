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
from datetime import datetime, timezone
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()
dynamodb = boto3.resource('dynamodb')

@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context: LambdaContext):
    """
    Calculate legislation compliance for a job by checking all clauses.
    Returns True if all clauses are compliant with legislation, False otherwise.
    """
    job_id = event['JobId']
    clauses_table_name = event.get('ClausesTableName', os.environ.get('CLAUSES_TABLE'))
    jobs_table_name = os.environ.get('JOBS_TABLE')
    
    clauses_table = dynamodb.Table(clauses_table_name)
    jobs_table = dynamodb.Table(jobs_table_name)
    
    logger.info(f"Calculating legislation compliance for job {job_id}")
    
    # Query all clauses for this job
    response = clauses_table.query(
        KeyConditionExpression='job_id = :job_id',
        ExpressionAttributeValues={':job_id': job_id}
    )
    
    clauses = response.get('Items', [])
    
    # Check if all clauses are compliant with legislation
    legislation_compliant = True
    
    for clause in clauses:
        additional_checks = clause.get('additional_checks', {})
        legislation_check = additional_checks.get('legislation_check')
        
        if legislation_check and not legislation_check.get('compliant', True):
            legislation_compliant = False
            logger.info(f"Clause {clause.get('clause_number')} is not compliant with legislation")
            break
    
    logger.info(f"Legislation compliance result: {legislation_compliant}")
    
    # Update job with legislation compliance and end date
    jobs_table.update_item(
        Key={'id': job_id},
        UpdateExpression='SET legislation_compliant = :compliant',
        ExpressionAttributeValues={
            ':compliant': legislation_compliant
        }
    )
    
    return {
        'JobId': job_id,
        'LegislationCompliant': legislation_compliant
    }
