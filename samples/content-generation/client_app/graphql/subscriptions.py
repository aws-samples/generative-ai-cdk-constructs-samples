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
    # Subscription to get updates on ingestion job status
    # More info: https://github.com/awslabs/generative-ai-cdk-constructs/tree/main/src/patterns/gen-ai/aws-rag-appsync-stepfn-opensearch
    UPDATE_INGESTION_JOB_STATUS = """
        subscription UpdateIngestionJobStatus($ingestionjobid: ID!) {
            updateIngestionJobStatus(ingestionjobid: $ingestionjobid) {
                ingestionjobid
                files {
                    name
                    status
                }
            }
        }
    """

    # Subscription to get updates on summary job status
    # More info: https://github.com/awslabs/generative-ai-cdk-constructs/tree/main/src/patterns/gen-ai/aws-summarization-appsync-stepfn
    UPDATE_SUMMARY_JOB_STATUS = """  
        subscription UpdateSummaryJobStatus($summary_job_id: ID) {
            updateSummaryJobStatus(summary_job_id: $summary_job_id) {
                summary_job_id
                files {
                    name
                    status 
                    summary
                }
            }
        }
    """
    # Subscription to get updates on Q&A job status
    # More info: https://github.com/awslabs/generative-ai-cdk-constructs/tree/main/src/patterns/gen-ai/aws-qa-appsync-opensearch
    UPDATE_QA_JOB_STATUS = """
        subscription UpdateQAJobStatus($jobid: ID!) {
            updateQAJobStatus(jobid: $jobid) {
                question
                answer
                jobstatus
            }
        }
    """
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