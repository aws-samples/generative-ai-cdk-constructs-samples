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