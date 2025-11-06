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

import typer
import sys
import os
from pathlib import Path
import boto3
from typing import Optional

# Add lambda function to path
sys.path.insert(0, str(Path(__file__).parent.parent / "check_legislation" / "lambda" / "legislation_fn" / "src"))

from model import Legislation
from repository.kb_legislation_repository import KBLegislationRepository
from repository.opensearch_client import OpenSearchLegislationClient
from repository.bedrock_agent_client import BedrockAgentLegislationClient

AWS_REGION = os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("AWS_REGION") or boto3.Session().region_name

app = typer.Typer(help="Legislation CLI for ingesting and listing legislations using KBLegislationRepository")

def upload_local_file_to_s3(local_path: str, bucket_name: str, s3_prefix: str, region: str = AWS_REGION) -> str:
    """Upload a local file to S3 and return the S3 key."""
    s3_client = boto3.client('s3', region_name=region)

    file_path = Path(local_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Local file not found: {local_path}")

    # Generate S3 key with prefix and original filename
    s3_key = f"{s3_prefix.rstrip('/')}/{file_path.name}"

    typer.echo(f"Uploading {local_path} to s3://{bucket_name}/{s3_key}")

    try:
        s3_client.upload_file(str(file_path), bucket_name, s3_key)
        typer.echo(f"Successfully uploaded to S3: {s3_key}")
        return s3_key
    except Exception as e:
        typer.echo(f"Error uploading file to S3: {e}", err=True)
        raise typer.Exit(1)

def get_stack_output(stack_name: str, output_key: str, region: str = AWS_REGION) -> str:
    """Get CloudFormation stack output value."""
    cf = boto3.client('cloudformation', region_name=region)
    try:
        response = cf.describe_stacks(StackName=stack_name)
        outputs = response['Stacks'][0].get('Outputs', [])
        for output in outputs:
            if output['OutputKey'] == output_key:
                return output['OutputValue']
        raise ValueError(f"Output {output_key} not found in stack {stack_name}")
    except Exception as e:
        typer.echo(f"Error fetching {output_key} from stack {stack_name}: {e}", err=True)
        raise typer.Exit(1)

def get_optional_param(value: Optional[str], stack_name: str, output_key: str, param_name: str, region: str = AWS_REGION) -> str:
    """Get parameter value or fetch from CloudFormation if not provided."""
    if value is not None:
        return value
    typer.echo(f"Fetching {param_name} from {stack_name}...")
    return get_stack_output(stack_name, output_key, region)

@app.command()
def list_legislations(
    aoss_endpoint: Optional[str] = typer.Option(None, help="OpenSearch Serverless endpoint"),
    index_name: str = typer.Option("bedrock-knowledge-base-default-index", help="Vector index name"),
    kb_id: Optional[str] = typer.Option(None, help="Knowledge Base ID"),
    data_source_id: Optional[str] = typer.Option(None, help="Data Source ID"),
    metadata_field: str = typer.Option("", help="Metadata field prefix (empty for root level)"),
    region: str = typer.Option(AWS_REGION, help="AWS region"),
):
    """List all legislations from the knowledge base."""
    # Get required parameters from CloudFormation if not provided
    aoss_endpoint = get_optional_param(aoss_endpoint, "CheckLegislationStack", "CheckLegislationAOSSEndpointURL", "AOSS endpoint", region)
    kb_id = get_optional_param(kb_id, "CheckLegislationStack", "CheckLegislationAgentKnowledgeBaseId", "Knowledge Base ID", region)
    data_source_id = get_optional_param(data_source_id, "CheckLegislationStack", "CheckLegislationAgentDataSourceId", "Data Source ID", region)

    # Create client instances
    opensearch_client = OpenSearchLegislationClient(
        aoss_endpoint=aoss_endpoint,
        index_name=index_name
    )

    bedrock_agent_client = BedrockAgentLegislationClient(
        kb_id=kb_id,
        data_source_id=data_source_id,
        bucket_name="dummy"  # Not needed for listing
    )

    repo = KBLegislationRepository(
        opensearch_client=opensearch_client,
        bedrock_agent_client=bedrock_agent_client
    )

    legislations = repo.list_legislations()
    typer.echo(f"Found {len(legislations)} legislations:")
    for leg in legislations:
        typer.echo(f"  Subject Matter: {leg.subject_matter}, ID: {leg.id}, Name: {leg.name}, S3 Key: {leg.s3_key}")

@app.command()
def ingest_legislation(
    law_id: str = typer.Option(..., help="Legislation ID"),
    law_name: str = typer.Option(..., help="Legislation name"),
    subject_matter: Optional[str] = typer.Option(None, help="The subject matter, e.g. Tax, Labor, Consumer, etc. Defaults to law_id if not provided"),
    s3_key: Optional[str] = typer.Option(None, help="S3 key for the legislation document (use this OR local_file)"),
    local_file: Optional[str] = typer.Option(None, help="Local PDF file path to upload (use this OR s3_key)"),
    s3_prefix: str = typer.Option("legislation", help="S3 prefix for uploaded files (only used with local_file)"),
    aoss_endpoint: Optional[str] = typer.Option(None, help="OpenSearch Serverless endpoint"),
    index_name: str = typer.Option("bedrock-knowledge-base-default-index", help="Vector index name"),
    kb_id: Optional[str] = typer.Option(None, help="Knowledge Base ID"),
    data_source_id: Optional[str] = typer.Option(None, help="Data Source ID"),
    bucket_name: Optional[str] = typer.Option(None, help="S3 bucket name"),
    wait: bool = typer.Option(False, help="Wait for ingestion to complete"),
    region: str = typer.Option(AWS_REGION, help="AWS region")
):
    """Ingest a legislation document into the knowledge base."""

    # Validate input parameters
    if not s3_key and not local_file:
        typer.echo("Error: Either --s3-key or --local-file must be provided", err=True)
        raise typer.Exit(1)

    if s3_key and local_file:
        typer.echo("Error: Cannot specify both --s3-key and --local-file", err=True)
        raise typer.Exit(1)

    # Get required parameters from CloudFormation if not provided
    aoss_endpoint = get_optional_param(aoss_endpoint, "CheckLegislationStack", "CheckLegislationAOSSEndpointURL", "AOSS endpoint", region)
    kb_id = get_optional_param(kb_id, "CheckLegislationStack", "CheckLegislationAgentKnowledgeBaseId", "Knowledge Base ID", region)
    data_source_id = get_optional_param(data_source_id, "CheckLegislationStack", "CheckLegislationAgentDataSourceId", "Data Source ID", region)
    bucket_name = get_optional_param(bucket_name, "CheckLegislationStack", "LegislationBucketName", "bucket name", region)

    # Handle local file upload if provided
    if local_file:
        s3_key = upload_local_file_to_s3(local_file, bucket_name, s3_prefix, region)

    # Create client instances
    opensearch_client = OpenSearchLegislationClient(
        aoss_endpoint=aoss_endpoint,
        index_name=index_name
    )

    bedrock_agent_client = BedrockAgentLegislationClient(
        kb_id=kb_id,
        data_source_id=data_source_id,
        bucket_name=bucket_name,
        wait_on_ingest=wait
    )

    repo = KBLegislationRepository(
        opensearch_client=opensearch_client,
        bedrock_agent_client=bedrock_agent_client
    )

    # Default subject_matter to law_id if not provided
    if subject_matter is None:
        subject_matter = law_id

    legislation = Legislation(id=law_id, subject_matter=subject_matter, name=law_name, s3_key=s3_key)

    typer.echo(f"Ingesting legislation: {law_name} (ID: {law_id})")
    result_id = repo.ingest_legislation(legislation)
    typer.echo(f"Successfully submitted legislation for ingestion with ID: {result_id}")
    if not wait:
        typer.echo("Note: Ingestion is running in the background. Use list-legislations to check when it's indexed.")

if __name__ == "__main__":
    app()