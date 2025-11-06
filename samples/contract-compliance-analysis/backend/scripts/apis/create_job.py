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

"""
Script to create a new job via the POST /jobs API.
This script uses CloudFormation exports to dynamically retrieve resource information.

Usage examples:
  # Create a job with minimal parameters
  python create_job.py service_contract_example.txt

  # Create a job with all parameters
  python create_job.py service_contract_example.txt --description "Contract analysis for service agreement" --language pt_BR --legal-compliance --legal-reference legal_reference.pdf --verbose

  # Use custom stack name
  python create_job.py service_contract_example.txt --stack-name MainBackendStack
"""

import argparse
import json
import logging
import os
import sys
import getpass
from urllib.parse import urljoin
from datetime import datetime, timedelta

import boto3
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def save_token(token):
    """Save token to a cache file with expiry time (1 hour from now)."""
    expiry_time = datetime.now() + timedelta(hours=1)
    try:
        with open(os.path.join(os.path.dirname(__file__), '.token_cache'), 'w') as f:
            json.dump({
                'token': token,
                'expires_at': expiry_time.isoformat()
            }, f)
        logger.debug("Token saved to cache file")
    except Exception as e:
        logger.debug(f"Could not save token to cache: {e}")


def load_token():
    """Load token from cache file if it exists and is not expired."""
    try:
        cache_file = os.path.join(os.path.dirname(__file__), '.token_cache')
        if not os.path.exists(cache_file):
            return None

        with open(cache_file, 'r') as f:
            data = json.load(f)
            expires_at = datetime.fromisoformat(data['expires_at'])
            if datetime.now() < expires_at:
                logger.debug("Using cached token")
                return data['token']
            else:
                logger.debug("Cached token has expired")
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        logger.debug(f"Could not load token from cache: {e}")
    return None


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Create a new job via the POST /jobs API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a job with minimal parameters
  python create_job.py service_contract_example.docx

  # Create a job with description and language
  python create_job.py service_contract_example.docx --description "Contract analysis for service agreement" --language pt_BR --verbose

  # Create a job with legal compliance
  python create_job.py service_contract_example.docx --legal-compliance --legal-reference "LEI_123" --verbose
        """
    )

    parser.add_argument('document_s3_key',
                        help='S3 key of the document to analyze')

    parser.add_argument('--description',
                        help='Job description for UX identification')

    parser.add_argument('--language',
                        choices=['pt_BR', 'en', 'es'],
                        help='Output language for the analysis')

    parser.add_argument('--legal-compliance',
                        action='store_true',
                        help='Enable legal compliance check')

    parser.add_argument('--legal-reference',
                        help='Legislation ID for legal compliance check (required if --legal-compliance is used)')

    parser.add_argument('--contract-type-id',
                        default='service-agreement',
                        help='Contract type ID (default: service-agreement)')

    parser.add_argument('--stack-name',
                        default=os.environ.get('STACK_NAME', 'MainBackendStack'),
                        help='CloudFormation stack name (default: MainBackendStack)')

    parser.add_argument('--region',
                        default=os.environ.get('AWS_REGION'),
                        help='AWS region (defaults to AWS CLI default region if not specified)')



    parser.add_argument('--verbose', '-v',
                        action='store_true',
                        help='Enable verbose logging')

    return parser.parse_args()


def get_stack_exports(stack_name, region):
    """Get CloudFormation stack exports."""
    logger.info(f"Retrieving CloudFormation exports for stack: {stack_name}")
    if region:
        logger.info(f"Using region: {region}")

    client_kwargs = {}
    if region:
        client_kwargs['region_name'] = region

    cfn = boto3.client('cloudformation', **client_kwargs)
    try:
        response = cfn.list_exports()
        exports = {}

        # Filter exports by stack name prefix
        for export in response.get('Exports', []):
            if export['Name'].startswith(stack_name):
                # Store with simplified key (without stack name prefix)
                key = export['Name'].replace(stack_name, '')
                exports[key] = export['Value']

        return exports
    except Exception as e:
        logger.error(f"Failed to retrieve stack exports: {e}")
        sys.exit(1)


def get_cognito_token(user_pool_id, client_id, username, password, region):
    """Get Cognito ID token for API authentication."""
    logger.info(f"Getting Cognito token for user: {username}")

    client_kwargs = {}
    if region:
        client_kwargs['region_name'] = region

    client = boto3.client('cognito-idp', **client_kwargs)
    try:
        response = client.initiate_auth(
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            },
            ClientId=client_id
        )

        # Check if the user needs to change password
        if response.get('ChallengeName') == 'NEW_PASSWORD_REQUIRED':
            logger.info("Password change required. Please set a new password.")
            new_password = getpass.getpass("New password: ")
            confirm_password = getpass.getpass("Confirm new password: ")

            if new_password != confirm_password:
                logger.error("Passwords do not match")
                sys.exit(1)

            # Respond to the challenge
            challenge_response = client.respond_to_auth_challenge(
                ClientId=client_id,
                ChallengeName='NEW_PASSWORD_REQUIRED',
                Session=response['Session'],
                ChallengeResponses={
                    'USERNAME': username,
                    'NEW_PASSWORD': new_password
                }
            )

            return challenge_response['AuthenticationResult']['IdToken']

        return response['AuthenticationResult']['IdToken']
    except Exception as e:
        logger.error(f"Failed to get Cognito token: {e}")
        sys.exit(1)


def create_job(api_endpoint, token, payload):
    """Create a new job via the POST /jobs API."""
    document_key = payload.get('documentS3Key') or payload.get('filename')
    logger.info(f"Creating new job for document: {document_key}")

    try:
        response = requests.post(
            urljoin(api_endpoint, "jobs"),
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30
        )

        if response.status_code == 200:
            job_data = response.json()
            logger.info(f"Successfully created job: {job_data.get('id')}")
            logger.info(f"Job status: {job_data.get('status')}")
            logger.info(f"Start date: {job_data.get('start_date')}")
            if 'description' in job_data:
                logger.info(f"Description: {job_data.get('description')}")
            if 'outputLanguage' in job_data:
                logger.info(f"Output language: {job_data.get('outputLanguage')}")
            if 'checkLegalCompliance' in job_data:
                logger.info(f"Legal compliance: {job_data.get('checkLegalCompliance')}")
            return True
        else:
            logger.error(f"Failed to create job")
            logger.error(f"Status code: {response.status_code}")

            # Try to parse JSON response for more details
            try:
                error_data = response.json()
                logger.error(f"Response: {error_data}")

                # Look for detailed error information
                if isinstance(error_data, dict):
                    if 'errors' in error_data:
                        logger.error("Validation errors:")
                        for error in error_data['errors']:
                            logger.error(f"  - {error}")
                    elif 'errorMessage' in error_data:
                        logger.error(f"Error message: {error_data['errorMessage']}")
            except:
                # If JSON parsing fails, show raw text
                logger.error(f"Response: {response.text}")

            return False

    except Exception as e:
        logger.error(f"Error creating job: {e}")
        return False


def main():
    """Main function."""
    args = parse_arguments()

    # Set log level based on verbose flag
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Validate legal compliance arguments
    if args.legal_compliance and not args.legal_reference:
        logger.error("--legal-reference is required when --legal-compliance is used")
        sys.exit(1)

    # Get CloudFormation stack exports
    stack_exports = get_stack_exports(args.stack_name, args.region)

    # Log available exports for debugging
    if args.verbose:
        logger.debug("Available CloudFormation exports:")
        for key, value in stack_exports.items():
            logger.debug(f"  {key}: {value}")

    # Get API endpoint from stack exports
    api_endpoint = stack_exports.get('ApiGatewayRestApiEndpoint')
    if not api_endpoint:
        logger.error("API endpoint not found in stack exports")
        logger.error("Available exports: " + ", ".join(stack_exports.keys()))
        sys.exit(1)

    # Get token from cache or prompt for credentials
    token = load_token()

    if not token:
        user_pool_id = stack_exports.get('CognitoUserPoolId')
        client_id = stack_exports.get('CognitoUserPoolClientId')

        if not user_pool_id or not client_id:
            logger.error("Cognito user pool ID or client ID not found in stack exports")
            logger.error("Available exports: " + ", ".join(stack_exports.keys()))
            sys.exit(1)

        # Prompt for credentials
        username = input("Cognito username: ")
        password = getpass.getpass("Cognito password: ")

        token = get_cognito_token(user_pool_id, client_id, username, password, args.region)

        # Save token for future use
        save_token(token)

    # Build payload
    payload = {
        "documentS3Key": args.document_s3_key,
        "contractTypeId": args.contract_type_id
    }

    if args.description:
        payload["jobDescription"] = args.description

    if args.language:
        payload["outputLanguage"] = args.language

    if args.legal_compliance:
        payload["additionalChecks"] = {
            "legislationCheck": {
                "legislationId": args.legal_reference
            }
        }

    logger.info(f"Request payload: {payload}")

    # Create the job
    success = create_job(api_endpoint, token, payload)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
