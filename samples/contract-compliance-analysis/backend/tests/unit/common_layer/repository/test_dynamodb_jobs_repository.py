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

from datetime import datetime
import pytest

from model import Job
from repository.dynamo_db_jobs_repository import DynamoDBJobsRepository

@pytest.fixture
def table_name():
  return 'test-jobs-table'

@pytest.fixture
def table(dynamodb_resource, table_name):
    """Get the session-scoped jobs table and clear it before each test"""
    table = dynamodb_resource.Table(table_name)

    # Clear any existing items before each test
    scan_result = table.scan()
    with table.batch_writer() as batch:
        for item in scan_result.get('Items', []):
            batch.delete_item(Key={'id': item['id']})

    return table

def test_can_record_job(dynamodb_client, table, table_name):
  # given
  repo = DynamoDBJobsRepository(table_name=table_name)
  job = Job(id="foo", document_s3_key="bar", contract_type_id="service-agreement", description="XXX")

  # when
  repo.record_job(job)

  # then
  result = dynamodb_client.get_item(TableName=table_name, Key={'id': {'S': job.id}})

  assert "Item" in result
  retrieved_job = result["Item"]
  assert retrieved_job["document_s3_key"]["S"] == job.document_s3_key
  assert retrieved_job["contract_type_id"]["S"] == job.contract_type_id
  assert retrieved_job["description"]["S"] == job.description

def test_it_loads_completed_job(table_with_completed_job, jobs_table_name, job_id):
  # given
  repo = DynamoDBJobsRepository(table_name=jobs_table_name)

  # when
  job = repo.get_job(job_id)

  # then
  assert job.unknown_total == 5
  assert job.contract_type_id == "service-agreement"

  job_dict = job.model_dump()
  assert "total_clause_types_by_risk" in job_dict
  assert "total_compliance_by_impact" in job_dict


def test_get_jobs_without_filter_returns_all_jobs(ddb, table, table_name):
  # given
  repo = DynamoDBJobsRepository(table_name=table_name)

  # Create jobs with different contract types
  job1 = Job(id="job1", document_s3_key="doc1.pdf", contract_type_id="service-agreement", description="Job 1")
  job2 = Job(id="job2", document_s3_key="doc2.pdf", contract_type_id="employment-contract", description="Job 2")
  job3 = Job(id="job3", document_s3_key="doc3.pdf", contract_type_id="service-agreement", description="Job 3")

  # Add created_at for GSI and use proper DynamoDB format
  for job in [job1, job2, job3]:
    item = job.model_dump()
    item['created_at'] = job.id  # Use job ID as created_at for simplicity
    # Convert to proper DynamoDB format, handling None values
    ddb_item = {}
    for k, v in item.items():
      if v is not None:
        ddb_item[k] = {'S': str(v)}
    ddb.put_item(TableName=table_name, Item=ddb_item)

  # when
  jobs = repo.get_jobs()

  # then
  assert len(jobs) == 3
  job_ids = [job.id for job in jobs]
  assert "job1" in job_ids
  assert "job2" in job_ids
  assert "job3" in job_ids


def test_get_jobs_with_contract_type_filter_returns_filtered_jobs(ddb, table, table_name):
  # given
  repo = DynamoDBJobsRepository(table_name=table_name)

  # Create jobs with different contract types
  job1 = Job(id="job1", document_s3_key="doc1.pdf", contract_type_id="service-agreement", description="Job 1")
  job2 = Job(id="job2", document_s3_key="doc2.pdf", contract_type_id="employment-contract", description="Job 2")
  job3 = Job(id="job3", document_s3_key="doc3.pdf", contract_type_id="service-agreement", description="Job 3")

  # Add created_at for GSI and use proper DynamoDB format
  for job in [job1, job2, job3]:
    item = job.model_dump()
    item['created_at'] = job.id  # Use job ID as created_at for simplicity
    # Convert to proper DynamoDB format, handling None values
    ddb_item = {}
    for k, v in item.items():
      if v is not None:
        ddb_item[k] = {'S': str(v)}
    ddb.put_item(TableName=table_name, Item=ddb_item)

  # when
  jobs = repo.get_jobs(contract_type_id="service-agreement")

  # then
  assert len(jobs) == 2
  job_ids = [job.id for job in jobs]
  assert "job1" in job_ids
  assert "job3" in job_ids
  assert "job2" not in job_ids


def test_get_jobs_with_nonexistent_contract_type_returns_empty_list(ddb, table, table_name):
  # given
  repo = DynamoDBJobsRepository(table_name=table_name)

  # Create a job
  job1 = Job(id="job1", document_s3_key="doc1.pdf", contract_type_id="service-agreement", description="Job 1")
  item = job1.model_dump()
  item['created_at'] = job1.id
  # Convert to proper DynamoDB format, handling None values
  ddb_item = {}
  for k, v in item.items():
    if v is not None:
      ddb_item[k] = {'S': str(v)}
  ddb.put_item(TableName=table_name, Item=ddb_item)

  # when
  jobs = repo.get_jobs(contract_type_id="nonexistent-type")

  # then
  assert len(jobs) == 0
