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

import boto3
import os
import re
from aws_lambda_powertools import Logger
from llm import invoke_llm_with_document
from util import (
    extract_last_item_from_tagged_list,
    extract_items_from_tagged_list,
    replace_placeholders,
)
from app_properties_manager import AppPropertiesManager

# Task name for parameter lookup
APP_TASK_NAME = 'ContractPreprocessing'

logger = Logger(service="contract-compliance-analysis")
s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

properties = AppPropertiesManager(cache_ttl=0)
clauses_table_name = os.environ["CLAUSES_TABLE_NAME"]

# Configuration constants
MAX_EXTRACTION_ITERATIONS = 10

CLAUSE_EXTRACTION_PROMPT = """I need your help to extract all clauses from the contract document.
{last_clause_section}
A clause is a distinct section or provision within a contract that deals with a particular subject matter or obligation.
In some cases, clauses are separated by punctuation like periods, semicolons, or line breaks. In other cases, clauses are delineated by section headings or numbered/lettered paragraphs. Some clauses can contain sub-items or bullet points. The sub-items and bullet points must not be separated from their parent clause.

Return each clause as a separate item with:
- clause_text: the full text of the clause

Begin by carefully reading the contract.
Then take a deep breath, think step by step and enclose all your thoughts within <thinking> tags, exploring multiple angles and approaches.
Identify the individual clauses within the contract.
Make sure all extracted text preserves the original content (and language - English, Spanish, Portuguese...) from the contract document, hence verbatim. I am sure you will do your best.

Write your final answer between <answer></answer> tags, which their inside is expected to comprise all extracted clauses, each individual clause wrapped between distinct <clause></clause> tags. So the answer should be something like:
<answer>
<clause>First clause text here</clause>
<clause>Second clause text here</clause>
<clause>Third clause text here</clause>
...
</answer>
"""

@logger.inject_lambda_context(log_event=True)
def handler(event, context):
    job_id = event.get("ExecutionName")
    logger.set_correlation_id(
        job_id
    )  # Use job_id as correlation ID for all log entries

    logger.info("PDF processing function started", extra={"job_id": job_id})

    try:
        document_s3_path = event["document_s3_path"]

        # Get model_id from Parameter Store with fallback
        model_id = properties.get_parameter('LanguageModelId', task_name=APP_TASK_NAME, default='us.amazon.nova-pro-v1:0')

        # Auto-detect document format from file extension
        file_extension = document_s3_path.split(".")[-1].lower()
        supported_formats = {"pdf": "pdf", "docx": "docx", "doc": "docx", "txt": "txt"}

        if file_extension not in supported_formats:
            raise ValueError(
                f"Unsupported file format: .{file_extension}. Supported formats: {', '.join(supported_formats.keys())}"
            )

        document_format = supported_formats[file_extension]

        logger.info(
            f"Processing document with format: {document_format}",
            extra={"job_id": job_id},
        )

        # Check for existing clauses to handle Lambda retry
        table = dynamodb.Table(clauses_table_name)
        existing_clauses_response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("job_id").eq(job_id),
            ScanIndexForward=False,  # Get latest first
            Limit=1,
        )

        next_clause_number = 0
        last_clause_from_db = ""  # For Lambda retries

        if existing_clauses_response["Items"]:
            last_clause = existing_clauses_response["Items"][0]
            next_clause_number = last_clause["clause_number"] + 1
            last_clause_from_db = last_clause["text"]
            logger.info(
                f"Starting from clause {next_clause_number} (continuing after clause {last_clause['clause_number']})",
                extra={"job_id": job_id},
            )

        # Loop to handle truncated responses
        max_iterations = MAX_EXTRACTION_ITERATIONS
        total_clauses_extracted = 0
        previous_iteration_last_clause = ""  # Initialize for subsequent iterations

        for iteration in range(max_iterations):
            logger.info(
                f"Starting extraction iteration {iteration + 1}/{max_iterations}",
                extra={"job_id": job_id},
            )

            # Get last clause text for continuation prompt
            last_clause_text = ""
            if iteration == 0 and last_clause_from_db:
                # First iteration: use the clause from DynamoDB (Lambda retry)
                last_clause_text = last_clause_from_db
            elif iteration > 0 and previous_iteration_last_clause:
                # Subsequent iterations: use the last clause we just extracted (iteration retry)
                last_clause_text = previous_iteration_last_clause

            # Build prompt using template and placeholders
            last_clause_section = ""
            if last_clause_text:
                last_clause_section = f"""
I already did myself some prior work and I could already extract up to this clause:
<latest_extracted_clause>{last_clause_text}</latest_extracted_clause>

So you need to start extracting from the next clause onwards. """

            prompt = replace_placeholders(
                CLAUSE_EXTRACTION_PROMPT, {"last_clause_section": last_clause_section}
            )

            response = invoke_llm_with_document(
                prompt=prompt,
                model_id=model_id,
                document_s3_uri=document_s3_path,
                document_format=document_format,
                max_new_tokens=4096,
                temperature=0.01,
                verbose=True,
            )

            logger.info(f"stop_reason: {response.stop_reason}")

            # Check if response was truncated
            was_truncated = response.stop_reason == "max_tokens"
            if was_truncated:
                logger.warning(
                    f"LLM response was truncated due to max_tokens limit (iteration {iteration + 1})",
                    extra={"job_id": job_id},
                )

                # Check if <answer> tag is opened but not properly closed
                if re.search(r"<answer>(?!.*</answer>)", response.output, re.DOTALL):
                    response.output += "</answer>"
                    logger.warning(
                        "Added missing </answer> tag due to truncation",
                        extra={"job_id": job_id},
                    )

            # Parse the response to extract clauses
            content = extract_last_item_from_tagged_list(response.output, "answer")

            # Extract individual clauses from <clause> tags
            clause_texts = extract_items_from_tagged_list(content, "clause")

            # Convert to the expected format with clause numbers
            clauses_data = [
                {
                    "text": clause_text.strip(),
                    "clause_number": next_clause_number + i,
                }
                for i, clause_text in enumerate(clause_texts)
            ]

            # Store clauses in DynamoDB
            if clauses_data:
                table = dynamodb.Table(clauses_table_name)
                with table.batch_writer() as batch:
                    for clause in clauses_data:
                        batch.put_item(
                            Item={
                                "job_id": job_id,
                                "clause_number": clause["clause_number"],
                                "text": clause["text"],
                            }
                        )

                total_clauses_extracted += len(clauses_data)
                next_clause_number += len(clauses_data)  # Update for next iteration
                previous_iteration_last_clause = clauses_data[-1]["text"]

                logger.info(
                    f"Iteration {iteration + 1}: Extracted {len(clauses_data)} clauses",
                    extra={
                        "job_id": job_id,
                        "iteration_clauses": len(clauses_data),
                        "total_clauses": total_clauses_extracted,
                    },
                )
            else:
                logger.info(
                    f"Iteration {iteration + 1}: No clauses extracted",
                    extra={"job_id": job_id},
                )

            # If response wasn't truncated, we're done
            if not was_truncated:
                logger.info(
                    f"Extraction completed after {iteration + 1} iterations",
                    extra={
                        "job_id": job_id,
                        "total_clauses": total_clauses_extracted,
                        "reason": "complete"
                        if not was_truncated
                        else "no_more_clauses",
                    },
                )
                break
        else:
            # Loop completed without breaking (hit max iterations)
            logger.warning(
                f"Reached maximum iterations ({max_iterations}) - extraction may be incomplete",
                extra={"job_id": job_id, "total_clauses": total_clauses_extracted},
            )

        logger.info(
            "Document processed and clauses stored",
            extra={
                "job_id": job_id,
                "clauses_count": total_clauses_extracted,
                "document_format": document_format,
            },
        )

        # Return format expected by Step Function (matching original preprocessing lambda)
        # ClauseNumbers should include ALL clauses (existing + newly extracted)
        total_clause_count = next_clause_number  # This is the next number to assign, so total count
        return {
            "JobId": job_id,
            "ContractTypeId": event.get("ContractTypeId"),  # Pass through contract type
            "ClauseNumbers": list(range(total_clause_count)),
            "OutputLanguage": event.get("OutputLanguage"),
            "AdditionalChecks": event.get("AdditionalChecks", {}),
        }

    except Exception as e:
        logger.error(
            "Document processing failed",
            extra={"job_id": event.get("job_id"), "error": str(e)},
        )
        raise

