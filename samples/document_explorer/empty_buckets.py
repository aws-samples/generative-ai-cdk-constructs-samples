import json
import os
import sys

import boto3
from botocore.exceptions import ClientError

cdk_deploy_output_file = 'apistack-outputs.json'

if os.path.isfile(cdk_deploy_output_file):
    with open(cdk_deploy_output_file) as cdk_deploy_output:
        parsed_json = json.load(cdk_deploy_output)

        s3 = boto3.resource('s3')
        client = boto3.client('s3')

        try:
            def empty_bucket(bucket_name):
                bucket = s3.Bucket(bucket_name)
                if s3.BucketVersioning(bucket_name).status == 'Enabled':
                    bucket.object_versions.all().delete()
                else:
                    bucket.objects.all().delete()

                response_get_bucket_logging = client.get_bucket_logging(Bucket=bucket_name)
                if 'LoggingEnabled' in response_get_bucket_logging and 'TargetBucket' in response_get_bucket_logging['LoggingEnabled']:
                    logging_bucket = s3.Bucket(response_get_bucket_logging['LoggingEnabled']['TargetBucket'])
                    if logging_bucket.versioning.status == 'Enabled':
                        logging_bucket.object_versions.filter(Prefix=response_get_bucket_logging['LoggingEnabled']['TargetPrefix']).delete()
                    else:
                        logging_bucket.objects.filter(Prefix=response_get_bucket_logging['LoggingEnabled']['TargetPrefix']).delete()

                return

            persistence_stack = 'PersistenceStack'
            empty_bucket(parsed_json[persistence_stack]["S3InputBucket"])
            empty_bucket(parsed_json[persistence_stack]["S3ProcessedBucket"])

            exit(0)

        except ClientError as client_error:
            if client_error.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f'User pool, "{user_pool_id}", or client, "{app_client_id}" not found', file=sys.stderr)
            raise client_error

exit(1)