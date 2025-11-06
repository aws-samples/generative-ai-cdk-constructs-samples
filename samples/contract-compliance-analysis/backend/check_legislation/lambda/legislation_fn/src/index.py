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

from aws_lambda_powertools.event_handler import APIGatewayRestResolver, CORSConfig
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools import Logger

from service.legislation import LegislationApi
from repository.kb_legislation_repository import KBLegislationRepository
from repository.opensearch_client import OpenSearchLegislationClient
from repository.bedrock_agent_client import BedrockAgentLegislationClient

# Note: origins are restricted via API Gateway settings
cors_config = CORSConfig()
app = APIGatewayRestResolver(cors=cors_config, enable_validation=True)
logger = Logger()

opensearch_client = OpenSearchLegislationClient(
    aoss_endpoint=os.environ["AOSS_ENDPOINT"],
    index_name=os.environ["LEGISLATION_KB_VECTOR_DB_INDEX"],
    metadata_field=os.environ.get("KB_METADATA_FIELD", ""),
    region=os.environ.get("AWS_REGION", "us-east-1"),
)

bedrock_agent_client = BedrockAgentLegislationClient(
    kb_id=os.environ["LEGISLATION_KB_ID"],
    data_source_id=os.environ["LEGISLATION_KB_DATA_SOURCE_ID"],
    bucket_name=os.environ.get("LEGISLATION_BUCKET_NAME"),
    region=os.environ.get("AWS_REGION", "us-east-1"),
    wait_on_ingest=False,
    logger=logger,
)

repo = KBLegislationRepository(
    opensearch_client=opensearch_client,
    bedrock_agent_client=bedrock_agent_client,
)

api = LegislationApi(legislation_repository=repo)

app.get("/legislations")(api.list_legislations)
app.post("/legislations")(api.ingest_legislation)

@logger.inject_lambda_context(log_event=True)
def handler(event: dict, context: LambdaContext) -> dict:
  return app.resolve(event, context)
