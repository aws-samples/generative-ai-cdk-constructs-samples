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
