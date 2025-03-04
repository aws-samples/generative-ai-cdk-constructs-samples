# Usage

## Overview

The code expert system evaluates code repositories against a set of guidelines using generative AI. The process
involves:

1. Uploading a code repository
2. Starting a code review
3. Waiting for results
4. Downloading findings

## Prerequisites

- AWS CLI configured with appropriate permissions
- A zipped code repository to evaluate
- The State Machine ARN (available in CloudFormation outputs)
- S3 bucket names (available in CloudFormation outputs)

## Getting Started

First, get your resource information from the CloudFormation stack outputs:

```shell
aws cloudformation describe-stacks --stack-name CodeExpert --query 'Stacks[0].Outputs'
```

Sample output:

```json
[
  {
    "OutputKey": "InputBucketName",
    "OutputValue": "code-expert-inputbucket-1h0zbro1ysu7z"
  },
  {
    "OutputKey": "OutputBucketName",
    "OutputValue": "code-expert-outputbucket-8s7pyxq2m4e9"
  },
  {
    "OutputKey": "StateMachineArn",
    "OutputValue": "arn:aws:states:us-east-1:123456789012:stateMachine:CodeExpert"
  }
]
```

Save these values for use in subsequent commands:

```shell
INPUT_BUCKET="code-expert-inputbucket-1h0zbro1ysu7z"
OUTPUT_BUCKET="code-expert-outputbucket-8s7pyxq2m4e9"
STATE_MACHINE_ARN="arn:aws:states:us-east-1:123456789012:stateMachine:CodeExpert"
```

## Input Format

To start a code review, provide:

1. A zip file containing the code repository
2. The model ID to use for evaluation
3. Whether to use multiple evaluation mode (evaluating multiple rules in one model invocation)

The Step Functions input schema is:

```
{
  "repo_key": "string",  // S3 key of the uploaded repository zip
  "model_id": "string",  // Bedrock model ID
  "multiple_evaluation": boolean  // Whether to evaluate multiple rules per invocation
}
```

## Starting a Code Review

1. Upload the repository:

```bash
aws s3 cp code.zip s3://${INPUT_BUCKET}/dataset/code.zip
```

Sample output:

```shell
upload: ./code.zip to s3://code-expert-inputbucket-1h0zbro1ysu7z/dataset/code.zip
```

2. Start the Step Functions execution:

```bash
aws stepfunctions start-execution \
  --state-machine-arn ${STATE_MACHINE_ARN} \
  --name "code_review_$(date +%s)" \
  --input '{
    "repo_key": "dataset/code.zip",
    "model_id": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    "multiple_evaluation": false
  }'
```

Sample output:

```json 
{
  "executionArn": "arn:aws:states:us-east-1:123456789012:execution:CodeExpert:code_review_1709543898",
  "startDate": "2024-03-04T12:31:38.793000+00:00"
}
```

Save the executionArn:

```shell 
EXECUTION_ARN="arn:aws:states:us-east-1:123456789012:execution:CodeExpert:code_review_1709543898"
```

## Monitoring Progress

Check execution status:

```bash
aws stepfunctions describe-execution \
  --execution-arn ${EXECUTION_ARN}
```

Sample output while running:

```json
{
  "executionArn": "arn:aws:states:us-east-1:123456789012:execution:CodeExpert:code_review_1709543898",
  "stateMachineArn": "arn:aws:states:us-east-1:123456789012:stateMachine:CodeExpert",
  "name": "code_review_1709543898",
  "status": "RUNNING",
  "startDate": "2024-03-04T12:31:38.793000+00:00"
}
```

Sample output when complete:

```json
{
  "executionArn": "arn:aws:states:us-east-1:123456789012:execution:CodeExpert:code_review_1709543898",
  "stateMachineArn": "arn:aws:states:us-east-1:123456789012:stateMachine:CodeExpert",
  "name": "code_review_1709543898",
  "status": "SUCCEEDED",
  "startDate": "2024-03-04T12:31:38.793000+00:00",
  "stopDate": "2024-03-04T13:45:22.104000+00:00",
  "output": "{\"processFindings\":{\"bucket\":\"code-expert-outputbucket-8s7pyxq2m4e9\",\"key\":\"findings/code_review_1709543898.json\",\"errors_key\":\"errors/code_review_1709543898.json\"}}"
}
```

## Downloading Results

Get the findings:

```bash
aws s3 cp s3://${OUTPUT_BUCKET}/findings/code_review_1709543898.json findings.json
```

Sample findings content:

```json   
[
    {
        "rule": "JAVA001",
        "file": "src/main/java/com/example/service/UserService.java",
        "snippet": "@Autowired\nprivate UserRepository userRepository;",
        "description": "Field injection is being used instead of constructor injection. This makes the class harder to test and obscures its dependencies.",
        "suggestion": "Use constructor injection instead. Replace the field injection with a final field and add a constructor:\n\nprivate final UserRepository userRepository;\n\n@Autowired\npublic UserService(UserRepository userRepository) {\n    this.userRepository = userRepository;\n}"
    }
]
```

Get any errors:

```bash
aws s3 cp s3://${OUTPUT_BUCKET}/errors/code_review_1709543898.json errors.json
```

Sample errors content:

```json
[
  {
    "file": "src/main/java/com/example/config/SecurityConfig.java",
    "error": "Failed to process record: ModelResponseError: Output missing tool use",
    "rules": [
      "SEC001",
      "SEC002"
    ]
  }
]
```

## Output Format

When the execution succeeds, the output includes S3 locations for the findings and any errors:

```
{
  "processFindings": {
    "bucket": "string",    // S3 bucket containing results
    "key": "string",      // S3 key for findings JSON
    "errors_key": "string"    // S3 key for errors JSON (if any)
  }
}
```

The findings JSON contains an array of findings:

```
[
  {
    "rule": "string",    // Rule ID
    "file": "string",    // File path where issue was found
    "snippet": "string", // Relevant code snippet
    "description": "string",    // Description of the issue
    "suggestion": "string"    // Suggested improvement
  }
]
```

## Supported Models

The system supports the following Bedrock models:

- Claude 3 Haiku
- Claude 3.5 Haiku
- Claude 3.5 Sonnet
- Claude 3.5 Sonnet v2
- Claude 3.7
- Nova Micro
- Nova Lite
- Nova Pro

You can optionally use cross-region inference for higher throughput by using the regional model IDs (e.g., 
"us.anthropic.claude-3-5-sonnet-20241022-v2:0" instead of "anthropic.claude-3-5-sonnet-20241022-v2:0").