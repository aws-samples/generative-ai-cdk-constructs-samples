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
import logging
import os

import boto3
from boto3.dynamodb.conditions import Key

from util import get_prompt_vars_dict

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL', 'WARNING').upper())

PROMPT_VARS = os.environ.get('PROMPT_VARS', "")

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
    print(f"Got job_id from event: {job_id}")
    return job_id


def get_job_clauses(job_id):
    print('Getting clauses from DynamoDB')
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


def get_clause_types():
    print('Getting guidelines from DynamoDB')
    clauses = []
    scan_kwargs = {}
    done = False
    start_key = None
    while not done:
        if start_key:
            scan_kwargs['ExclusiveStartKey'] = start_key
        response = guidelines_table.scan(**scan_kwargs)
        clauses.extend(response.get('Items', []))
        start_key = response.get('LastEvaluatedKey', None)
        done = start_key is None
    return clauses


def update_job(job_id, total_clause_types_by_risk, total_compliance_by_impact, total_clauses_with_unknown_type,
               needs_review):
    print('Getting job from DynamoDB')
    response = jobs_table.get_item(Key={'id': job_id})
    if 'Item' not in response:
        raise ValueError(f'Job not found')
    job = response['Item']
    job['total_compliance_by_impact'] = total_compliance_by_impact
    job['total_clause_types_by_risk'] = total_clause_types_by_risk
    job['unknown_total'] = total_clauses_with_unknown_type
    job['needs_review'] = needs_review

    jobs_table.put_item(Item=job)
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
            print(f"Invalid Impact: {impact}")
        clause_types_by_impact[impact].append(ct['type_id'])

    return clause_types_by_impact


def get_totals(job_clauses, clause_types_by_impact):
    print('Calculating totals')
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
    print('Calculating risk')
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


def check_review(clause_types_by_risk):
    print('Checking if needs review')
    prompt_vars_dict = get_prompt_vars_dict(PROMPT_VARS)

    clause_types_by_risk['high']['threshold'] = int(prompt_vars_dict.get('high_risk_threshold', 0))
    clause_types_by_risk['medium']['threshold'] = int(prompt_vars_dict.get('medium_risk_threshold', 1))
    clause_types_by_risk['low']['threshold'] = int(prompt_vars_dict.get('low_risk_threshold', 3))
    needs_review = False
    for risk in ['high', 'medium', 'low']:
        if clause_types_by_risk[risk]['quantity'] > clause_types_by_risk[risk]['threshold']:
            needs_review = True
            break
    return needs_review, clause_types_by_risk


def handler(event, _context):
    job_id = parse_event(event)
    job_clauses = get_job_clauses(job_id)
    clause_types = get_clause_types()
    clause_types_by_impact = get_clause_types_by_impact(clause_types)
    total_compliance_by_impact, total_clauses_with_unknown_type = get_totals(job_clauses, clause_types_by_impact)
    total_clause_types_by_risk, total_compliance_by_impact = calculate_risk(total_compliance_by_impact)
    needs_review, total_clause_types_by_risk = check_review(total_clause_types_by_risk)
    return update_job(job_id, total_clause_types_by_risk, total_compliance_by_impact, total_clauses_with_unknown_type,
                      needs_review)
