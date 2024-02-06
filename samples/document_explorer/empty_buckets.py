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
                print(f"emptying s3://{bucket_name}/{prefix}...")
                bucket = s3.Bucket(bucket_name)
                if s3.BucketVersioning(bucket_name).status == 'Enabled':
                    bucket.object_versions.filter(Prefix=prefix).delete()
                else:
                    bucket.objects.filter(Prefix=prefix).delete()
                # Best effort log delivery removal:
                # Deletions from above may still be delivered, so may not be empty even after being emptied.
                # https://docs.aws.amazon.com/AmazonS3/latest/userguide/ServerLogs.html#LogDeliveryBestEffort
                response_get_bucket_logging = client.get_bucket_logging(Bucket=bucket_name)
                if 'LoggingEnabled' in response_get_bucket_logging and 'TargetBucket' in response_get_bucket_logging['LoggingEnabled']:
                    logging_bucket_name = response_get_bucket_logging['LoggingEnabled']['TargetBucket']
                    logging_prefix = response_get_bucket_logging['LoggingEnabled']['TargetPrefix']
                    time.sleep(5)
                    empty_bucket(logging_bucket_name, logging_prefix)
                return

            persistence_stack = 'PersistenceStack'
            empty_bucket(parsed_json[persistence_stack]["S3InputBucket"])
            empty_bucket(parsed_json[persistence_stack]["S3ProcessedBucket"])

            exit(0)

        except ClientError as client_error:
            raise client_error

exit(1)