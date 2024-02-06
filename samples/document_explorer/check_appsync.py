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
import json
import os
import sys

import boto3
from botocore.exceptions import ClientError
import requests
from requests_aws4auth import AWS4Auth

cdk_deploy_output_file = 'apistack-outputs.json'

if os.path.isfile(cdk_deploy_output_file):
    with open(cdk_deploy_output_file) as cdk_deploy_output:
        parsed_json = json.load(cdk_deploy_output)
        api_stack='ApiStack'
        session = requests.Session()
        credentials = boto3.session.Session().get_credentials()
        session.auth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            boto3.session.Session().region_name,
            'appsync',
            session_token=credentials.token
        )
        APPSYNC_API_ENDPOINT_URL = parsed_json[api_stack]["GraphQLEndpoint"]

        def call_graphql(query, method='POST'):
            # Now we can simply post the request...
            response = session.request(
                url=APPSYNC_API_ENDPOINT_URL,
                method='POST',
                json={'query': query}
            )
            return response

        schema_query = """
            query {
            __schema {
                __typename
            }
            }
        """
        response_graphql = call_graphql(schema_query)
        assert response_graphql.status_code == 200, response_graphql.status_code
        assert response_graphql.json()['data']['__schema']['__typename'] == '__Schema', response_graphql.text
