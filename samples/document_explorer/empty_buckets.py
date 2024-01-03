import json
import os
import sys
import time

import boto3
from botocore.exceptions import ClientError

cdk_deploy_output_file = 'apistack-outputs.json'

if os.path.isfile(cdk_deploy_output_file):
    with open(cdk_deploy_output_file) as cdk_deploy_output:
        parsed_json = json.load(cdk_deploy_output)

        s3 = boto3.resource('s3')
        client = boto3.client('s3')

        try:
            def empty_bucket(bucket_name, prefix=""):
                bucket = s3.Bucket(bucket_name)
                if s3.BucketVersioning(bucket_name).status == 'Enabled':
                    bucket.object_versions.filter(Prefix=prefix).delete()
                else:
                    bucket.objects.filter(Prefix=prefix).delete()

                # Best effort log delivery removal:
                time.sleep(60)
                # Deletions from above may still be delivered, so may not be empty even after being emptied.
                # https://docs.aws.amazon.com/AmazonS3/latest/userguide/ServerLogs.html#LogDeliveryBestEffort
                response_get_bucket_logging = client.get_bucket_logging(Bucket=bucket_name)
                if 'LoggingEnabled' in response_get_bucket_logging and 'TargetBucket' in response_get_bucket_logging['LoggingEnabled']:
                    logging_bucket_name = response_get_bucket_logging['LoggingEnabled']['TargetBucket']
                    logging_prefix = response_get_bucket_logging['LoggingEnabled']['TargetPrefix']
                    empty_bucket(logging_bucket_name, logging_prefix)
                return

            persistence_stack = 'PersistenceStack'
            empty_bucket(parsed_json[persistence_stack]["S3InputBucket"])
            empty_bucket(parsed_json[persistence_stack]["S3ProcessedBucket"])

            exit(0)

        except ClientError as client_error:
            raise client_error

exit(1)