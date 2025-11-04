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
from boto3.dynamodb.conditions import Key
from aws_lambda_powertools import Logger
from app_properties_manager import AppPropertiesManager
from repository.dynamo_db_contract_type_repository import DynamoDBContractTypeRepository

# Task name for parameter lookup
APP_TASK_NAME = 'ContractRiskCalculation'

logger = Logger()

dynamodb = boto3.resource('dynamodb')
jobs_table = dynamodb.Table(os.environ['JOBS_TABLE'])
clauses_table = dynamodb.Table(os.environ['CLAUSES_TABLE'])
guidelines_table = dynamodb.Table(os.environ['GUIDELINES_TABLE'])


class MalformedRequest(ValueError):
    pass


def parse_event(event):
    if "JobId" in event:
        job_id = event["JobId"]
    else:
        raise MalformedRequest("Unknown event structure")
    logger.info(f"Parsed job_id from event: {job_id}")
    return job_id


def get_job_clauses(job_id):
    logger.info('Getting clauses from DynamoDB')
    clauses = []
    query_kwargs = {
        'KeyConditionExpression': Key('job_id').eq(job_id)
    }
    done = False
    start_key = None
    while not done:
        if start_key:
            query_kwargs['ExclusiveStartKey'] = start_key
        response = clauses_table.query(**query_kwargs)
        clauses.extend(response.get('Items', []))
        start_key = response.get('LastEvaluatedKey', None)
        done = start_key is None
    return clauses


def get_clause_types(contract_type_id):
    logger.info(f'Getting guidelines from DynamoDB for contract type: {contract_type_id}')
    clauses = []
    query_kwargs = {
        'KeyConditionExpression': Key('contract_type_id').eq(contract_type_id)
    }
    done = False
    start_key = None
    while not done:
        if start_key:
            query_kwargs['ExclusiveStartKey'] = start_key
        response = guidelines_table.query(**query_kwargs)
        clauses.extend(response.get('Items', []))
        start_key = response.get('LastEvaluatedKey', None)
        done = start_key is None
    return clauses


def update_job(job_id, total_clause_types_by_risk, total_compliance_by_impact, total_clauses_with_unknown_type,
               guidelines_compliant):
    logger.info('Getting job from DynamoDB')
    response = jobs_table.get_item(Key={'id': job_id})
    if 'Item' not in response:
        raise ValueError(f'Job not found')
    job = response['Item']

    logger.info("Updating job with risk assessment results", extra={
        "guidelines_compliant": guidelines_compliant,
        "unknown_total": total_clauses_with_unknown_type
    })

    # Update only the analysis results, preserving existing fields
    try:
        jobs_table.update_item(
            Key={'id': job['id']},
            UpdateExpression='SET total_compliance_by_impact = :impact, total_clause_types_by_risk = :risk, unknown_total = :unknown, guidelines_compliant = :guidelines_compliant',
            ExpressionAttributeValues={
                ':impact': total_compliance_by_impact,
                ':risk': total_clause_types_by_risk,
                ':unknown': total_clauses_with_unknown_type,
                ':guidelines_compliant': guidelines_compliant
            }
        )
        logger.info("Successfully updated job with risk assessment results")
    except Exception as e:
        logger.error("Failed to update job with risk assessment results", extra={"error": str(e)})
        raise

    # Return updated job for response
    job['total_compliance_by_impact'] = total_compliance_by_impact
    job['total_clause_types_by_risk'] = total_clause_types_by_risk
    job['unknown_total'] = total_clauses_with_unknown_type
    return job


def get_clause_types_by_impact(clause_types):
    clause_types_by_impact = {
        'low': [],
        'medium': [],
        'high': [],
    }
    for ct in clause_types:
        impact = str(ct['level']).lower()
        if impact not in clause_types_by_impact:
            logger.warning(f"Invalid Impact: {impact}")
        clause_types_by_impact[impact].append(ct['clause_type_id'])

    return clause_types_by_impact


def get_totals(job_clauses, clause_types_by_impact):
    logger.info('Calculating totals')
    total_clauses_with_unknown_type = 0
    job_clause_analyses_by_clause_type = {}
    for job_clause in job_clauses:
        for job_clause_analysis in job_clause['types']:
            type_id = job_clause_analysis['type_id']
            if type_id.upper() == 'UNKNOWN':
                total_clauses_with_unknown_type += 1
            else:
                if type_id in job_clause_analyses_by_clause_type:
                    job_clause_analyses_by_clause_type[type_id].append(job_clause_analysis)
                else:
                    job_clause_analyses_by_clause_type[type_id] = [job_clause_analysis]
    total_compliance_by_impact = {}
    for impact, clause_types in clause_types_by_impact.items():
        total_compliance_by_impact[impact] = {
            'compliant': {
                'quantity': 0,
            },
            'non_compliant': {
                'quantity': 0,
            },
            'missing': {
                'quantity': 0,
            },
        }
        for type_id in clause_types:
            if type_id in job_clause_analyses_by_clause_type:
                compliant = True
                for job_clause_analysis in job_clause_analyses_by_clause_type[type_id]:
                    compliant &= job_clause_analysis['compliant']
                if compliant:
                    total_compliance_by_impact[impact]['compliant']['quantity'] += 1
                else:
                    total_compliance_by_impact[impact]['non_compliant']['quantity'] += 1
            else:  # clause type missing
                total_compliance_by_impact[impact]['missing']['quantity'] += 1
    return total_compliance_by_impact, total_clauses_with_unknown_type


def calculate_risk(total_compliance_by_impact):
    logger.info('Calculating risk')
    clause_types_by_risk = {
        'none': {
            'quantity': 0,
        },
        'low': {
            'quantity': 0,
        },
        'medium': {
            'quantity': 0,
        },
        'high': {
            'quantity': 0,
        },
    }

    total_compliance_by_impact['low']['compliant']['risk'] = 'none'
    total_compliance_by_impact['medium']['compliant']['risk'] = 'none'
    total_compliance_by_impact['high']['compliant']['risk'] = 'none'
    total_compliance_by_impact['low']['non_compliant']['risk'] = 'low'
    total_compliance_by_impact['medium']['non_compliant']['risk'] = 'medium'
    total_compliance_by_impact['high']['non_compliant']['risk'] = 'high'
    total_compliance_by_impact['low']['missing']['risk'] = 'medium'
    total_compliance_by_impact['medium']['missing']['risk'] = 'high'
    total_compliance_by_impact['high']['missing']['risk'] = 'high'

    for risk in clause_types_by_risk:
        for impact in total_compliance_by_impact:
            for compliance in total_compliance_by_impact[impact]:
                if total_compliance_by_impact[impact][compliance]['risk'] == risk:
                    clause_types_by_risk[risk]['quantity'] += total_compliance_by_impact[impact][compliance]["quantity"]

    return clause_types_by_risk, total_compliance_by_impact


def check_review(clause_types_by_risk, contract_type_id):
    logger.info('Checking compliance against risk thresholds')

    # Get contract type-specific risk thresholds from ContractTypesTable
    contract_type_repo = DynamoDBContractTypeRepository(table_name=os.environ.get('CONTRACT_TYPES_TABLE'))
    contract_data = contract_type_repo.get_contract_type(contract_type_id)
    
    if not contract_data:
        raise ValueError(f"Contract type '{contract_type_id}' not found")
    if not contract_data.is_active:
        raise ValueError(f"Contract type '{contract_type_id}' is not active")

    clause_types_by_risk['high']['threshold'] = contract_data.high_risk_threshold
    clause_types_by_risk['medium']['threshold'] = contract_data.medium_risk_threshold
    clause_types_by_risk['low']['threshold'] = contract_data.low_risk_threshold

    compliant = True
    for risk in ['high', 'medium', 'low']:
        if clause_types_by_risk[risk]['quantity'] > clause_types_by_risk[risk]['threshold']:
            compliant = False
            break
    return compliant, clause_types_by_risk


@logger.inject_lambda_context(log_event=True)
def handler(event, _context):
    job_id = parse_event(event)
    contract_type_id = event.get("ContractTypeId")  # Get contract type from event
    logger.set_correlation_id(job_id)  # Use JobId as correlation ID for all log entries
    logger.info("Processing risk calculation")

    if not contract_type_id:
        logger.error("ContractTypeId not provided in event")
        raise ValueError("ContractTypeId is required")

    job_clauses = get_job_clauses(job_id)
    logger.info("Retrieved job clauses", extra={"clause_count": len(job_clauses)})

    clause_types = get_clause_types(contract_type_id)
    clause_types_by_impact = get_clause_types_by_impact(clause_types)

    total_compliance_by_impact, total_clauses_with_unknown_type = get_totals(job_clauses, clause_types_by_impact)
    logger.info("Calculated compliance totals", extra={
        "unknown_clauses": total_clauses_with_unknown_type,
        "compliance_summary": {
            "low_compliant": total_compliance_by_impact.get('low', {}).get('compliant', {}).get('quantity', 0),
            "medium_compliant": total_compliance_by_impact.get('medium', {}).get('compliant', {}).get('quantity', 0),
            "high_compliant": total_compliance_by_impact.get('high', {}).get('compliant', {}).get('quantity', 0),
            "medium_non_compliant": total_compliance_by_impact.get('medium', {}).get('non_compliant', {}).get('quantity', 0)
        }
    })

    total_clause_types_by_risk, total_compliance_by_impact = calculate_risk(total_compliance_by_impact)
    guidelines_compliant, total_clause_types_by_risk = check_review(total_clause_types_by_risk, contract_type_id)

    logger.info("Risk assessment completed", extra={
        "guidelines_compliant": guidelines_compliant,
        "risk_summary": {
            "none": total_clause_types_by_risk.get('none', {}).get('quantity', 0),
            "low": total_clause_types_by_risk.get('low', {}).get('quantity', 0),
            "medium": total_clause_types_by_risk.get('medium', {}).get('quantity', 0),
            "high": total_clause_types_by_risk.get('high', {}).get('quantity', 0)
        }
    })

    return update_job(job_id, total_clause_types_by_risk, total_compliance_by_impact, total_clauses_with_unknown_type,
                      guidelines_compliant)
