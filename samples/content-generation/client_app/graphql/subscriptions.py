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
class Subscriptions:
    # Subscription to get updates on image generation job status
    # More info: https://github.com/awslabs/generative-ai-cdk-constructs/tree/main/src/patterns/gen-ai/aws-imagegen-appsync-lambda
    UPDATE_GENERATE_IMAGE_JOB_STATUS = """
        subscription UpdateGenerateImageStatus($jobid: ID!) {
            updateGenerateImageStatus(jobid: $jobid) {
                filename
                input_text
                jobid
                message
                status
                image_path
            }
        }
    """