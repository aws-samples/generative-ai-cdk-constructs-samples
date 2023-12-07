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

        try:
            def empty_bucket(bucket_name):
                bucket = s3.Bucket(bucket_name)
                if s3.BucketVersioning(bucket_name).status == 'Enabled':
                    bucket.object_versions.delete()
                else:
                    bucket.objects.all().delete()
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