# Code Expert Core Components

This package contains the core implementation components for the Code Expert system, including:

* Business logic for code analysis and rule evaluation
* Lambda function handlers for AWS integration
* Docker task entrypoint for synchronous processing

## Components

### Business Logic

* Rule configuration and parsing
* Repository analysis
* AI model interaction and response processing
* Finding generation

### Lambda Handlers

* analyze_repo.py: Analyzes repository structure and prepares evaluation jobs
* process_findings.py: Processes AI model outputs and generates findings
* bedrock_inference_job_event.py: Handles Bedrock batch job events
* bedrock_create_model_invocation_job.py: Creates Bedrock model invocation jobs

### Docker Task

Provides synchronous processing capability when batch processing is not desired.

## Rule Evaluation Process

The following sequence diagram illustrates the interaction between components during the code review process:
<figure>

```mermaid
sequenceDiagram
    participant FM as FileManager
    participant RD as RuleDetector
    participant RM as RuleMapper
    participant ER as EvaluateRules
    participant BB as BedrockBatchInputProcessor
    FM ->> RD: Provide file list
    RD ->> RM: Determine applicable rules
    RM ->> ER: Map rules to files
    ER ->> BB: Prepare batch input
    BB ->> Bedrock: Submit batch job
    Bedrock -->> ER: Return results
    ER ->> S3: Store findings

```

<figcaption>Rule evaluation sequence</figcaption>
</figure>

## Testing

Tests are located in the tests/ directory. Run using pytest:

```shell
pytest
``` 

## Note

These components are designed to be deployed using the AWS infrastructure defined in packages/infra. For configuration
and deployment instructions, see the main project documentation.
