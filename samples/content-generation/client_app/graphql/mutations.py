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
            $responseGenerationMethod: ResponseGenerationMethod
            ) {
            postQuestion(
                jobid: $jobid
                jobstatus: $jobstatus
                filename: $filename
                question: $question
                max_docs: $max_docs
                verbose: $verbose
                streaming: $streaming
                responseGenerationMethod: $responseGenerationMethod
            ) {
                __typename
            }
        }
    """

    # GraphQL mutation string to generate image
    # More info: https://github.com/awslabs/generative-ai-cdk-constructs/tree/main/src/patterns/gen-ai/aws-imagegen-appsyn-lambda
    GENERATE_IMAGE = """
        mutation GenerateImage($imageInput: ImageInput!) {
            generateImage(imageInput: $imageInput) {
                __typename
            }
        }
    """