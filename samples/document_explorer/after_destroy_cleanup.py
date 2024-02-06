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


try:
    s3_client = boto3.client('s3')
    logs_client = boto3.client('logs')
    s3 = boto3.resource('s3')
    response_list_buckets = s3_client.list_buckets()

    def empty_bucket(bucket_name):
        bucket = s3.Bucket(bucket_name)
        if s3.BucketVersioning(bucket_name).status == 'Enabled':
            bucket.object_versions.delete()
        else:
            bucket.objects.all().delete()
        return

    for bucket in response_list_buckets['Buckets']:
        try:
            response_get_bucket_tagging = s3_client.get_bucket_tagging(Bucket=bucket['Name'])
            for tag in response_get_bucket_tagging['TagSet']:
                if tag['Key'] == 'app':
                    if tag['Value'] == "generative-ai-cdk-constructs-samples":
                        print(f'Deleting bucket "{bucket["Name"]}"...')
                        empty_bucket(bucket['Name'])
                        s3_client.delete_bucket(Bucket=bucket['Name'])                       
                    break
        except ClientError as client_error:
            if client_error.response['Error']['Code'] == 'NoSuchTagSet':
                None  # print(f'NoSuchTagSet found', file=sys.stderr)
            else:
                raise client_error

    log_group_paginator = logs_client.get_paginator('describe_log_groups')
    response_describe_log_groups_iterator = log_group_paginator.paginate()
    for response_describe_log_groups in response_describe_log_groups_iterator:
        for log_group in response_describe_log_groups["logGroups"]:
            print(f'Deleting log group "{log_group["logGroupName"]}"...')
            logs_client.delete_log_group(logGroupName=log_group['logGroupName'])

    exit(0)

except ClientError as client_error:
    raise client_error

exit(1)
