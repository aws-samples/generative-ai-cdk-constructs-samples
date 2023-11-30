class Mutations:

    # GraphQL mutation string to ingest documents
    # More info: https://github.com/awslabs/generative-ai-cdk-constructs/tree/main/src/patterns/gen-ai/aws-rag-appsync-stepfn-opensearch
    INGEST_DOCUMENTS = """
        mutation IngestDocuments($ingestionInput: IngestionDocsInput!) {
            ingestDocuments(ingestioninput: $ingestionInput) {
                __typename
            }
        }
    """

    # GraphQL mutation string to generate summaries
    # More info: https://github.com/awslabs/generative-ai-cdk-constructs/tree/main/src/patterns/gen-ai/aws-summarization-appsync-stepfn
    GENERATE_SUMMARY = """
        mutation GenerateSummary($summaryInput: SummaryDocsInput!) {
            generateSummary(summaryInput: $summaryInput) {
                __typename
            }
        }
    """

    # GraphQL mutation string to post a question and get an answer
    # More info: https://github.com/awslabs/generative-ai-cdk-constructs/tree/main/src/patterns/gen-ai/aws-qa-appsync-opensearch
    POST_QUESTION = """
        mutation PostQuestion(
            $jobid: ID
            $jobstatus: String  
            $filename: String
            $question: String
            $max_docs: Int
            $verbose: Boolean
            $streaming: Boolean
            ) {
            postQuestion(
                jobid: $jobid
                jobstatus: $jobstatus
                filename: $filename
                question: $question
                max_docs: $max_docs
                verbose: $verbose
                streaming: $streaming
            ) {
                __typename
            }
        }
    """