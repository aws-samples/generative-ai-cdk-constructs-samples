#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import os
from typing import Iterator, TYPE_CHECKING, Union, Optional, Callable

import jinja2
from pydantic import ValidationError

from amzn_code_expert_code_expert.models.chain_of_thought import ChainOfThought
from amzn_code_expert_code_expert.models.findings import RuleEvaluation, RuleFinding, ComplianceStatus, EvaluationError
from amzn_code_expert_code_expert.models.rules import Rule
from amzn_code_expert_code_expert.pace_core_utils.BedrockBatch.ConverseToBatch import InvokeModelInput, ModelResponse
from amzn_code_expert_code_expert.pace_core_utils.BedrockBatch.manifest import (
    BedrockBatchInputProcessor,
    random_record_id,
    PAD_PREFIX,
)
from amzn_code_expert_code_expert.pace_core_utils.BedrockBatch.output import BedrockBatchOutputProcessor
from amzn_code_expert_code_expert.pace_core_utils.BedrockBatch.persist_record_state import PersistRecordState
from amzn_code_expert_code_expert.pace_core_utils.boto3_helper.bedrock_runtime_client import (
    retry_bedrock_errors,
    invoke_model_with_input,
)
from amzn_code_expert_code_expert.pace_core_utils.exceptions import ModelResponseError
from amzn_code_expert_code_expert.pace_core_utils.logger import logger
from .file_manager import FileManager
from .rule_mapper import RuleMapper

if TYPE_CHECKING:
    from mypy_boto3_bedrock_runtime import BedrockRuntimeClient
    from mypy_boto3_bedrock_runtime.type_defs import ConverseResponseTypeDef


class FileReadError(Exception):
    pass


class RelevantContext:
    def __init__(self, file_manager: FileManager, filename: str):
        self.file_manager = file_manager
        self.filename = filename
        with open(os.path.join(file_manager.repo_path, filename), "r") as f:
            self.content = f.read()


ASSISTANT_PREFILL = '{"thinking": "'


def create_batch_manifests(*bedrock_batch_inputs: BedrockBatchInputProcessor) -> list[str]:
    """
    Combines multiple BedrockBatchInputProcessor queues into a single processor and generates manifest files.

    Args:
        *bedrock_batch_inputs: Variable number of BedrockBatchInputProcessor objects whose queues will be combined

    Returns:
        list[str]: List of S3 keys for the generated manifest files
    """
    combined_processor = bedrock_batch_inputs[0]
    for processor in bedrock_batch_inputs[1:]:
        combined_processor.queue.extend(processor.queue)
    return list(combined_processor.prepare_manifests())


def parse_rule_evaluation_findings(
    response: Union["ConverseResponseTypeDef", ModelResponse],
    prefill: Optional[str] = None,
) -> list[RuleFinding]:
    """
    Parses a Bedrock model response and extracts rule findings.

    Takes a raw response from a Bedrock model evaluation and processes it
    to extract any rule violations or findings. Handles parsing errors
    and edge cases in the response.

    Args:
        response: The raw response from the Bedrock model containing evaluation results
        prefill: Optional string to prepend to the model response text. Defaults to empty string.

    Returns:
        list[RuleFinding]: A list of RuleFinding objects representing the findings from evaluating the rules

    Raises:
        ModelResponseError: If the response cannot be parsed or contains invalid findings data

    Side Effects:
        - Logs information about the parsed response
        - Logs warnings for non-compliant evaluations without findings
        - Logs errors for response parsing failures
    """
    if not prefill:
        prefill = ""
    try:
        text = ""
        for content in response["output"]["message"]["content"]:
            if "text" in content:
                text = prefill + content["text"]
        logger.debug({"text": text})
        try:
            cot_response = ChainOfThought[RuleEvaluation].model_validate_json(text)
        except ValidationError as e:
            cot_response = recover_validation_error(e, text)
        logger.debug({"response": cot_response.model_dump()})
        rule_evaluation = cot_response.answer
        if not rule_evaluation.findings and rule_evaluation.complianceStatus == ComplianceStatus.NON_COMPLIANT:
            logger.warning(f"Non-compliant evaluation without findings")
            raise ModelResponseError("Non-compliant evaluation without findings")
        elif rule_evaluation.findings:
            return rule_evaluation.findings
        else:
            logger.info(f"No findings")
            return []
    except ModelResponseError as e:
        logger.error(f"Error parsing model response: {e}")
        logger.error(response)
        raise e


def recover_validation_error(e, text):
    logger.error(f"Error parsing response: {e}")
    logger.error({"text": text})
    if r"control character (\u0000-\u001F)" in str(e):
        cleaned_text = clean_json_text(text)
        logger.info(f"Cleaning response: {cleaned_text}")
        try:
            response = ChainOfThought[RuleEvaluation].model_validate_json(cleaned_text)
        except Exception as e:
            raise ModelResponseError(f"Failed to parse response: {e}")
    elif r"Invalid JSON: EOF while parsing" in str(e):
        cleaned_text = text + "}"
        logger.info(f"Trying with an additional closing brace: {cleaned_text}")
        try:
            response = ChainOfThought[RuleEvaluation].model_validate_json(cleaned_text)
        except Exception as e:
            raise ModelResponseError(f"Failed to parse response: {e}")
    elif r"Invalid JSON: trailing characters" in str(e):
        cleaned_text = text[0:-1].strip()
        logger.info(f"Try removing final character: {cleaned_text}")
        try:
            response = ChainOfThought[RuleEvaluation].model_validate_json(cleaned_text)
        except Exception as e:
            raise ModelResponseError(f"Failed to parse response: {e}")
    else:
        raise ModelResponseError(f"Failed to parse response: {e}")
    return response


def yield_rules_for_evaluation(rules: list[Rule], multiple_evaluation: bool, simple: bool) -> Iterator[list[Rule]]:
    """
    Yield rules for evaluation either one at a time or all together based on multiple_evaluation setting.

    Args:
        rules (list[Rule]): The list of rules to evaluate.
        multiple_evaluation (bool): Whether to evaluate multiple rules together.
        simple (bool): Whether the rules are simple or require context.

    Yields:
        list[Rule]: A list containing either a single rule or all rules.
    """
    if multiple_evaluation and simple:
        yield rules
    else:
        for rule in rules:
            yield [rule]


class RuleEvaluator:
    def __init__(
        self,
        file_manager: FileManager,
        rule_mapper: RuleMapper,
        prompt_templates: jinja2.Environment,
        model_id: str,
        multiple_evaluation=True,
    ):
        self.file_manager = file_manager
        self.rule_mapper = rule_mapper
        self.prompt_templates = prompt_templates
        self.model_id = model_id
        self.multiple_evaluation = multiple_evaluation

    def build_simple_rule_prompt(self, file: str, rules: list[Rule]) -> str:
        """
        Build a prompt for evaluating simple rules on a file.

        Args:
            file (str): The file path to evaluate.
            rules (list[Rule]): The list of rules to evaluate.

        Returns:
            str: A prompt for evaluating the rules on the file.

        Raises:
            FileReadError: If there is an error reading the file.
        """
        try:
            with open(os.path.join(self.file_manager.repo_path, file), "r") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading file {file}: {str(e)}")
            raise FileReadError(e)

        template = self.get_evaluate_rules_prompt_template()
        return template.render(
            rules=rules,
            content=content,
            filename=file,
            tool_name="structured_output",
            schema=ChainOfThought[RuleEvaluation].model_json_schema(),
        )

    def build_context_rule_prompt(self, file: str, rules: list[Rule]) -> str:
        """
        Build a prompt for evaluating rules that require additional context on a file.

        Args:
            file (str): The file path to evaluate.
            rules (list[Rule]): The list of rules to evaluate.

        Returns:
            str: A prompt for evaluating the rules on the file.
        """
        template = self.get_evaluate_rules_prompt_template()
        with open(os.path.join(self.file_manager.repo_path, file), "r") as f:
            content = f.read()

        relevant_context: list[RelevantContext] = []
        for rule in rules:
            for context_file in self.rule_mapper.context_files_by_rule[rule.rule]:
                relevant_context.append(RelevantContext(self.file_manager, context_file))

        return template.render(
            relevant_context=relevant_context,
            rules=rules,
            content=content,
            filename=file,
            schema=ChainOfThought[RuleEvaluation].model_json_schema(),
        )

    def build_simple_rule_invocation(self, prompt: str, prefill: Optional[str] = None) -> InvokeModelInput:
        """
        Prepare a Bedrock Converse API call to evaluate simple rules on a file.

        Args:
            prompt: The prompt to send to the model.
            prefill: Prefill the model's response

        Returns:
            InvokeModelInput: A Bedrock Converse API call to evaluate the rules.
        """

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "text": prompt,
                    }
                ],
            },
        ]
        if prefill:
            messages.append(
                {"role": "assistant", "content": [{"text": prefill}]},
            )
        input = InvokeModelInput(
            modelId=self.model_id,
            messages=messages,
            inferenceConfig={
                "maxTokens": 4096,
                "temperature": 0,
            },
        )

        return input

    def build_context_rule_invocation(self, prompt: str, prefill: Optional[str] = None) -> InvokeModelInput:
        """
        Prepare a Bedrock Converse API call to evaluate rules that require additional context on a file.

        Args:
            prompt: The prompt to send to the model.
            prefill: Prefill the model's response

        Returns:
            InvokeModelInput: A Bedrock Converse API call to evaluate the rules.
        """
        # Since additional context fits into the prompt, we can just use the same invocation as simple rules.
        return self.build_simple_rule_invocation(prompt, prefill)

    def get_evaluate_rules_prompt_template(self) -> jinja2.Template:
        return self.prompt_templates.get_template("evaluate_rules.jinja2")

    def evaluate_simple_rules(
        self, bedrock_runtime: "BedrockRuntimeClient" = None, heartbeat: Optional[Callable[[], None]] = None
    ) -> tuple[list[RuleFinding], list[EvaluationError]]:
        """
        Evaluate simple rules on all files and return findings.

        For each file with simple rules, call an LLM to evaluate the rules and parse the output.

        Returns:
            tuple[list[RuleFinding], list[EvaluationError]]: A tuple containing:
                - A list of RuleFinding objects representing the findings from evaluating the simple rules
                - A list of EvaluationError objects representing any errors that occurred during evaluation
        """
        findings: list[RuleFinding] = []
        errors: list[EvaluationError] = []

        for file, file_rules in self.rule_mapper.rules_by_file.items():
            for rules in yield_rules_for_evaluation(file_rules, self.multiple_evaluation, True):
                try:
                    if heartbeat:
                        heartbeat()
                    prompt = self.build_simple_rule_prompt(file, rules)
                    evaluation_findings = self.invoke_and_parse(bedrock_runtime, prompt, ASSISTANT_PREFILL)
                    findings.extend(evaluation_findings)
                except Exception as e:
                    logger.error(f"Error evaluating rules {[r.rule for r in rules]} on file {file}: {str(e)}")
                    errors.append(EvaluationError(file=file, error=str(e), rules=[r.rule for r in rules]))
                    continue

        return findings, errors

    def evaluate_context_rules(
        self, bedrock_runtime: "BedrockRuntimeClient" = None, heartbeat: Optional[Callable[[], None]] = None
    ) -> tuple[list[RuleFinding], list[EvaluationError]]:
        """
        Evaluate rules that require additional context on all files and return findings.

        For each file with context rules, call an LLM to evaluate the rules and parse the output.

        Returns:
            tuple[list[RuleFinding], list[EvaluationError]]: A tuple containing:
                - A list of RuleFinding objects representing the findings from evaluating the rules
                - A list of EvaluationError objects representing any errors that occurred during evaluation
        """
        findings: list[RuleFinding] = []
        errors: list[EvaluationError] = []

        for file, file_rules in self.rule_mapper.context_rules_by_context_file.items():
            for rules in yield_rules_for_evaluation(file_rules, self.multiple_evaluation, False):
                try:
                    if heartbeat:
                        heartbeat()
                    prompt = self.build_context_rule_prompt(file, rules)
                    evaluation_findings = self.invoke_and_parse(bedrock_runtime, prompt, ASSISTANT_PREFILL)
                    findings.extend(evaluation_findings)
                except Exception as e:
                    logger.error(f"Error evaluating rules {[r.rule for r in rules]} on file {file}: {str(e)}")
                    errors.append(EvaluationError(file=file, error=str(e), rules=[r.rule for r in rules]))
                    continue

        return findings, errors

    @retry_bedrock_errors
    def invoke_and_parse(
        self, bedrock_runtime: "BedrockRuntimeClient", prompt: str, prefill: Optional[str] = None
    ) -> list[RuleFinding]:
        invocation = self.build_context_rule_invocation(prompt, prefill)
        response = invoke_model_with_input(bedrock_runtime, **invocation)
        evaluation_findings = parse_rule_evaluation_findings(response, prefill)
        return evaluation_findings

    def prepare_batch_evaluate_simple_rules(
        self, bedrock_batch_input: BedrockBatchInputProcessor, persist_record_state: PersistRecordState
    ):
        """
        Prepare a Bedrock batch inference job to evaluate simple rules on all files.

        For each file with simple rules, prepare LLM inference and add it to a model inference job manifest.

        Args:
            bedrock_batch_input (BedrockBatchInputProcessor): The Bedrock batch input processor to use.
            persist_record_state (PersistRecordState): Where to store the record data

        Returns:
            list[str]: A list of S3 keys for model inference job manifests.
        """
        for file, file_rules in self.rule_mapper.rules_by_file.items():
            for rules in yield_rules_for_evaluation(file_rules, self.multiple_evaluation, True):
                try:
                    prompt = self.build_simple_rule_prompt(file, rules)
                    invocation = self.build_simple_rule_invocation(prompt, ASSISTANT_PREFILL)
                    record_id = random_record_id()
                    persist_record_state.add_record(record_id, {"file": file, "rules": [r.rule for r in rules]})
                    bedrock_batch_input.add_record(record_id, **invocation)
                except FileReadError as e:
                    logger.error(f"Error evaluating rules on file {file}: {str(e)}")
                    continue

    def prepare_batch_evaluate_context_rules(
        self, bedrock_batch_input: BedrockBatchInputProcessor, persist_record_state: PersistRecordState
    ):
        """
        Prepare a Bedrock batch inference job to evaluate rules that require additional context on all files.

        For each file with context rules, prepare LLM inference and add it to a model inference job manifest.

        Args:
            bedrock_batch_input (BedrockBatchInputProcessor): The Bedrock batch input processor to use.
            persist_record_state (PersistRecordState): Where to store the record data

        Returns:
            list[str]: A list of S3 keys for model inference job manifests.
        """
        for file, file_rules in self.rule_mapper.context_rules_by_context_file.items():
            for rules in yield_rules_for_evaluation(file_rules, self.multiple_evaluation, False):
                try:
                    prompt = self.build_context_rule_prompt(file, rules)
                    invocation = self.build_context_rule_invocation(prompt, ASSISTANT_PREFILL)
                    record_id = random_record_id()
                    persist_record_state.add_record(record_id, {"file": file, "rules": [r.rule for r in rules]})
                    bedrock_batch_input.add_record(record_id, **invocation)
                except FileReadError as e:
                    logger.error(f"Error evaluating rules on file {file}: {str(e)}")
                    continue


def process_batch_evaluate_simple_rules(
    bedrock_batch_output: BedrockBatchOutputProcessor, bucket: str, key: str, persist_record_state: PersistRecordState
) -> tuple[list[RuleFinding], list[EvaluationError]]:
    """
    Process the output of the Bedrock batch inference job and return findings.

    Args:
        bedrock_batch_output (BedrockBatchOutputProcessor): The Bedrock batch output processor to use.
        bucket (str): The S3 bucket with model inference job output.
        key (str): The S3 key of the model inference job output manifest to process.
        persist_record_state (PersistRecordState): Where to store the record data

    Returns:
        list[RuleFinding]: A list of RuleFinding objects representing the findings from evaluating the simple rules.
    """
    findings: list[RuleFinding] = []
    errors: list[EvaluationError] = []
    for response in bedrock_batch_output.process_output(bucket, key):
        if response["record_id"].startswith(PAD_PREFIX):
            continue
        # TODO: retry batch errors
        record = persist_record_state.get_record(response["record_id"])
        file: str = record.get("file", "unable to get filename")
        rules: list[str] = record.get("rules", ["unable to get rules"])
        if "error" in response:
            logger.error(f"Error processing record: {response['error']}")
            errors.append(
                EvaluationError(
                    file=file,
                    error=f"""{response["error"]["errorCode"]}: {response["error"]["errorMessage"]}""",
                    rules=rules,
                )
            )
            continue
        if "model_output" not in response:
            logger.error(f"No model output found for record {response['record_id']}")
            errors.append(EvaluationError(file=file, error="No model output found", rules=rules))
            continue
        try:
            findings.extend(parse_rule_evaluation_findings(response["model_output"], ASSISTANT_PREFILL))
        except Exception as e:
            logger.error(f"Error parsing model output for record {response['record_id']}: {str(e)}")
            errors.append(EvaluationError(file=file, error=str(e), rules=rules))
            continue
    return findings, errors


def process_batch_evaluate_context_rules(
    bedrock_batch_output: BedrockBatchOutputProcessor, bucket: str, key: str, persist_record_state: PersistRecordState
) -> tuple[list[RuleFinding], list[EvaluationError]]:
    """
    Process the output of the Bedrock batch inference job and return findings.

    Args:
        bedrock_batch_output (BedrockBatchOutputProcessor): The Bedrock batch output processor to use.
        bucket (str): The S3 bucket with model inference job output.
        key (str): The S3 key of the model inference job output manifest to process.
        persist_record_state (PersistRecordState): Where to store the record data

    Returns:
        list[RuleFinding]: A list of RuleFinding objects representing the findings from evaluating the simple rules.
    """
    # No special handling needed for context rules, just process the output as simple rules.
    return process_batch_evaluate_simple_rules(bedrock_batch_output, bucket, key, persist_record_state)


def clean_json_text(text: str) -> str:
    """
    Clean the JSON text by removing non-printable characters and escaping them.

    Args:
        text (str): The JSON text to clean.

    Returns:
        str: The cleaned JSON text.
    """
    cleaned_text = []
    in_quotes = False
    escape_chars = {"\n": "\\n", "\r": "\\r", "\t": "\\t"}

    for c in text:
        if c.isprintable():
            cleaned_text.append(c)
            if c == '"':
                in_quotes = not in_quotes
        elif in_quotes and c in escape_chars:
            cleaned_text.append(escape_chars[c])

    return "".join(cleaned_text)
