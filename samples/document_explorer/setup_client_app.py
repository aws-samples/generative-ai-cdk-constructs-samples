import base64
import hashlib
import hmac
import json
import os
import sys

import boto3
from botocore.exceptions import ClientError

cdk_deploy_output_file = 'apistack-outputs.json'

if os.path.isfile(cdk_deploy_output_file):
    with open(cdk_deploy_output_file) as cdk_deploy_output:
        parsed_json = json.load(cdk_deploy_output)

        api_stack='ApiStack'
        persistence_stack='PersistenceStack'
        

        app_client_id = parsed_json[api_stack]["ClientId"]
        user_pool_id = parsed_json[api_stack]["UserPoolId"]

        client = boto3.client('cognito-idp')

        try:
            response_describe_user_pool = client.describe_user_pool(
                UserPoolId=user_pool_id
            )
            response_describe_user_pool_client = client.describe_user_pool_client(
                UserPoolId=user_pool_id,
                ClientId=app_client_id
            )
            print(f'APP_URI="{parsed_json[api_stack]["AppUri"]}"')
            app_client_secret = response_describe_user_pool_client["UserPoolClient"]["ClientSecret"]
            print(f'CLIENT_SECRET="{app_client_secret}"')
            print(f'AUTHENTICATED_ROLE_ARN="{parsed_json[api_stack]["AuthenticatedRoleArn"]}"')
            print(f'CLIENT_ID="{app_client_id}"')
            print(f'COGNITO_DOMAIN="{parsed_json[api_stack]["CognitoDomain"]}"')
            print(f'GRAPHQL_ENDPOINT="{parsed_json[api_stack]["GraphQLEndpoint"]}"')
            print(f'IDENTITY_POOL_ID="{parsed_json[api_stack]["IdentityPoolId"]}"')
            print(f'REGION="{parsed_json[api_stack]["Region"]}"')
            print(f'USER_POOL_ID="{user_pool_id}"')
            print(f'S3_INPUT_BUCKET="{parsed_json[persistence_stack]["S3InputBucket"]}"')
            print(f'S3_PROCESSED_BUCKET="{parsed_json[persistence_stack]["S3ProcessedBucket"]}"')

            username = 'sample@example.com'
            key = bytes(app_client_secret, 'latin-1')
            msg = bytes(username + app_client_id, 'latin-1')
            new_digest = hmac.new(key, msg, hashlib.sha256).digest()
            secret_hash = base64.b64encode(new_digest).decode()

            response_sign_up = client.sign_up(
                ClientId=app_client_id,
                SecretHash=secret_hash,
                Username=username,
                Password='Sample123!'
            )
            response_admin_confirm_sign_up = client.admin_confirm_sign_up(
                UserPoolId=parsed_json[api_stack]["UserPoolId"],
                Username=username
            )
            response_admin_update_user_attributes = client.admin_update_user_attributes(
                UserPoolId=parsed_json[api_stack]["UserPoolId"],
                Username=username,
                UserAttributes=[
                    {
                        'Name': 'email_verified',
                        'Value': 'true'
                    }
                ]
            )
            exit(0)

        except ClientError as client_error:
            if client_error.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f'User pool, "{user_pool_id}", or client, "{app_client_id}" not found', file=sys.stderr)
            raise client_error

exit(1)
