# Contract Compliance Analysis - Backend

## Basic setup

You can run the setup from a local workspace.

### Setup steps

In order to deploy this project, you need to have installed:

- [Python](https://www.python.org/downloads/) 3.11 or higher
- [Docker](https://docs.docker.com/engine/install/)
- [AWS CDK Toolkit](https://docs.aws.amazon.com/cdk/v2/guide/cli.html)
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)

With all installed, run this command:

```shell
$ python3 -V && cdk --version && docker info -f "{{.OperatingSystem}}"
Python 3.12.2
2.135.0 (build d46c474)
Docker Desktop
```

An output similar to the above indicates that all is ok to proceed.

If any of these commands fails, you can revisit the documentation and check for possible steps you have forgotten to complete.
Ensure that your CDK version is using CDK V2, by checking if the second line of the output follows the pattern 2.*.*.

Having those installed, it is time to configure your environment to connect to your AWS Account.
To set up your local environment to use such an AWS account you can follow the steps described at [https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html)


#### Create Python virtual environment

To manually create a virtualenv on MacOS and Linux:

```shell
python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```shell
source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```shell
.venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```shell
pip install -r requirements.txt
```

#### Enable Bedrock Model Access (Prerequisite)

Before deploying the stack, ensure you have access to the required Amazon Bedrock models:

**Amazon Nova models** (default): Automatically available. Most features in this prototype have Amazon Nova Pro as the default model, so no action needed.

**Claude models** (optional): Required only if you plan to use Claude models or the [Legislation Check](#optional-feature-legislation-checks) feature. Requires a one-time use case submission per account. By using Claude models, you agree to the [Anthropic EULA](https://aws.amazon.com/legal/bedrock/third-party-models/).

**Option 1 - Using the provided script**:
```bash
python scripts/enable_anthropic_models.py \
  --company-name "Your Company" \
  --company-website "https://yourcompany.com" \
  --use-cases "Contract compliance analysis using AI" \
  --intended-users "0" \
  --industry "Technology"
```
(Or run without arguments for interactive mode)

**Option 2 - Via AWS Console**:
- Go to Amazon Bedrock → Model catalog → Select any Claude model → Submit use case form

After use case submission, marketplace subscription is handled automatically by Lambda functions on first invocation.

**New Claude models**: If Anthropic releases a new Claude model not yet in the IAM policy:
1. Get the product ID from [AWS documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-product-ids.html)
2. Add it to the `add_bedrock_marketplace_permissions()` function in `stack_constructs/lambda_constructs.py`
3. Redeploy with `cdk deploy`

#### Bootstrap CDK

Run the following

```shell
cdk bootstrap
```

#### Deployment

1. Run AWS CDK Toolkit to deploy the Backend stack with the runtime resources.

    ```shell
    cdk deploy MainBackendStack --require-approval=never
    ```

2. Any modifications made to the code can be applied to the deployed stack by running the same command again.

    ```shell
    cdk deploy MainBackendStack --require-approval=never
    ```

#### Populate Guidelines table

Once the Stack is setup, you need to populate the DynamoDB Contract Types and Guidelines tables with the data from the Guidelines JSON files that are included in the `guidelines` folder.

Navigate to the `scripts` folder and run the script to load the guidelines for your desired language(s):

```shell
cd scripts
```

**English guidelines (sample):**
```shell
python load_guidelines.py --json-file ../guidelines/guidelines_example.json
```

**Spanish guidelines (sample - Mexican legal terms):**
```shell
python load_guidelines.py --json-file ../guidelines/guidelines_example_es.json
```

**Portuguese guidelines (sample - Brazilian legal terms):**
```shell
python load_guidelines.py --json-file ../guidelines/guidelines_example_pt_BR.json
```

You can load one or more language versions depending on your needs. **Note:** These are sample guidelines for demonstration purposes and should be customized according to your specific legal requirements and use case.

#### Add users to Cognito User Pool

First, locate the Cognito User Pool ID, through the AWS CLI:

```shell
$ aws cloudformation describe-stacks --stack-name MainBackendStack --query "Stacks[0].Outputs[?contains(OutputKey, 'UserPoolId')].OutputValue"

[
    "OutputValue": "<region>_a1aaaA1Aa"
]
```

You can then go the Amazon Cognito page at the AWS Console, search for the User Pool and add users


## Managing Application Properties

### Using Configuration Scripts
The application uses AWS Systems Manager Parameter Store for configuration. You can manage parameters using the provided scripts:

```shell
# Create a new YAML configuration template
python scripts/init_app_properties.py  # Creates app_properties.yaml from template

# Sync YAML configuration to Parameter Store
python scripts/apply_app_properties.py --preview  # Preview changes
python scripts/apply_app_properties.py  # Apply changes
```

### Available Properties

Global parameters:
- `CompanyName`: Your company name (e.g., "AnyCompany")
- `LanguageModelId`: Amazon Bedrock model ID (e.g., "amazon.nova-lite-v1:0")

Task-specific overrides (prefix parameter with task name):
- `ContractPreprocessing/LanguageModelId`: Document preprocessing and clause extraction
- `ContractClassification/LanguageModelId`: Clause type classification
- `ContractEvaluation/LanguageModelId`: Clause compliance evaluation
- `GenerateEvaluationQuestions/LanguageModelId`: Evaluation question generation
- `GenerateClauseExamples/LanguageModelId`: Clause example generation
- `LegislationCheck/LanguageModelId`: Legislation compliance checking

Example configuration:
```yaml
# Global fallback
LanguageModelId: "amazon.nova-lite-v1:0"

# Use more powerful models for specific tasks
ContractEvaluation/LanguageModelId: "us.amazon.nova-pro-v1:0"
GenerateEvaluationQuestions/LanguageModelId: "amazon.nova-premier-v1:0"
```


## How to customize contract analysis according to your use case

This solution was designed to support analysis of contracts of different types and of different languages, based on the assumption that the contracts establish an agreement between two parties: a given company and another party. The solution already comes pre-configured with sample service contract guidelines in English, Spanish and Portuguese for the company *AnyCompany*. These sample guidelines serve as a starting point and should be customized according to your specific use case and legal requirements.

The customization of the contract analysis according to your specific use case comprises two major configuration artifacts:

- **Contract Types & Guidelines**: The application supports multiple contract types, each with its own set of guidelines that define the taxonomy of clause types and how to classify and evaluate contract clauses.
- **Application Properties**: Configuration settings such as company name and language model IDs (see [Managing Application Properties](#managing-application-properties)).

### Managing Contract Types and Guidelines

The frontend application includes a comprehensive management interface for contract types and guidelines:

- **Contract Type Management**: Create, view, and delete contract types through the UI
- **Guidelines Management**: Add, edit, and delete guidelines for each contract type with an intuitive form interface
- **AI-Assisted Generation**: Use AI to generate evaluation questions for guidelines automatically
- **Import from Reference Contracts**: Import contract types and their guidelines from existing reference contracts (see below)

Access these features through the frontend application after deployment.

### Customization Workflow

1. **Deploy the Backend stack**
2. **(Optional) Configure Application Parameters** using Parameter Store (see below). The system will use sensible defaults if not configured
3. **Access the frontend application** and navigate to the Contract Types management section
4. **Create a new contract type** or use the default "Service Agreement" type
5. **Add guidelines** for your contract type using one of these approaches:
   - **Manual Entry**: Use the guidelines form to add clause types and evaluation questions
   - **AI-Assisted Generation**: Automatically generate evaluation questions and review/edit as needed
   - **Import from Reference Contract**: Upload an existing contract to extract contract type, clause types, and initial guidelines (see below)

### Reference Contract Import

The reference contract import feature allows you to bootstrap a new contract type by analyzing an existing contract document:

**When to use:**
- Quickly set up a new contract type based on an existing template
- Understand the structure and clause types in a reference contract
- Accelerate the guidelines creation process

**How it works:**
1. Upload a reference contract document (PDF, DOCX, or TXT) via the frontend UI
2. The system uses AI to extract:
   - Contract type metadata (name, description, language)
   - Party roles (e.g., "Service Provider" and "Customer")
   - Clause types present in the contract
   - Initial guidelines and evaluation questions
3. Review and refine the imported data through the web UI
4. (Optional) Use AI-assisted generation to enhance guidelines:
   - Generate additional evaluation questions for each clause type
   - Create clause examples to help with classification
   - Review and edit AI-generated content as needed
5. The new contract type is ready to use for analyzing similar contracts

Access via: Frontend UI → Contract Types → Import from Reference Contract

## How to use a different Language Model on Amazon Bedrock

The application supports any Amazon Bedrock foundation model. You can configure different models globally or per-task based on your specific requirements (cost, latency, accuracy trade-offs).

For this example, we'll configure Amazon Nova Pro for more complex reasoning tasks:

- Update your `app_properties.yaml` file to change the `LanguageModelId` field, then apply the changes:

```yaml
# Global model setting - applies to all tasks
LanguageModelId: "us.amazon.nova-pro-v1:0"

# Or use task-specific overrides to mix different models
ContractEvaluation/LanguageModelId: "us.amazon.nova-pro-v1:0"
GenerateEvaluationQuestions/LanguageModelId: "anthropic.claude-3-5-haiku-20241022-v1:0"
```

```shell
# Update the parameter in Parameter Store
python scripts/apply_app_properties.py
```

Replace it with the model ID you want to use. The list of model IDs available through Amazon Bedrock is available in the [documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html). 

**Note**: When using cross-region inference profiles (model IDs starting with `us.`), the IAM permissions already include wildcard region support for both foundation models and inference profiles.


## OPTIONAL FEATURE: Legislation Checks

**ATTENTION** Current version of legislation checks uses Amazon Open Search Serverless, which has an estimated monthly cost of 350$.

**Model Requirements**: The Legislation Check agent uses Anthropic Claude 3.5 Haiku. Before deploying this feature, ensure you have enabled Claude model access by following the procedure in the [Enable Bedrock Model Access](#enable-bedrock-model-access-prerequisite) section.

If you would like to deploy the Legislation Checks feature of the Contract Analysis blueprint, you will follow the steps below:

1. Deploy CheckLegislationStack CDK stack
2. Add your first Legislation documents

### Deploy CDK stack with Legislation Check resources

```bash
cdk deploy CheckLegislationStack --require-approval=never
```

The output of this deployment will be something like this:

```bash
 ✅  CheckLegislationStack

✨  Deployment time: 56.37s

Outputs:
CheckLegislationStack.CheckLegislationAOSSEndpointURL = https://xxxxxx.us-east-1.aoss.amazonaws.com
CheckLegislationStack.CheckLegislationAgentDataSourceId = XXXXX
CheckLegislationStack.CheckLegislationAgentKnowledgeBaseId = XXXXX
```

Take note of all these values.

### Add your first legislation documents

You can index legislation documents into the deployed Amazon Bedrock Knowledge Base, that the agent will consult when evaluating your contracts, using a companion CLI tool.

The agent uses the `--law-id` identifier for determining which legislation document to use from the knowledge base.

For example, a contract being evaluated under the lens of Consumer Law in Brazil could use the Código de Defesa do Consumidor legislation.

You can find at samples/legislation folder a couple of legislation docs already available for indexing into the Knowledge Base. Feel free to choose what samples to index into the Knowledge Base.

**Option 1: Upload local PDF files directly (recommended):**

```bash
python scripts/legislation_cli.py ingest-legislation --law-id="br-constituicao-88-67ed" --law-name="Constituição Federal Brasileira de 1988, 67a edição" --local-file="samples/legislation/br-CF88_67ed.pdf" --wait
python scripts/legislation_cli.py ingest-legislation --law-id="br-codigo-civil" --law-name="Código Civil Brasileiro" --local-file="samples/legislation/br-codigo-civil-2a-ed.pdf" --wait
python scripts/legislation_cli.py ingest-legislation --law-id="br-cdc" --law-name="Código de Defesa do Consumidor" --local-file="samples/legislation/br-CDC_2025.pdf" --wait
python scripts/legislation_cli.py ingest-legislation --law-id="mx-codigo-civil-federal" --law-name="Código Civil Federal de México" --local-file="samples/legislation/mx-codigo-civil-federal.pdf" --wait
```

**Option 2: Use existing S3 files:**

```bash
# Get the legislation bucket name from stack outputs
LEGISLATION_BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name CheckLegislationStack --query "Stacks[0].Outputs[?OutputKey=='LegislationBucketName'].OutputValue" --output text)

aws s3 cp samples/legislation/ s3://<LEGISLATION_BUCKET_NAME>/legislation/ --recursive --exclude "*" --include "*.pdf"
python scripts/legislation_cli.py ingest-legislation --law-id="br-constituicao-88-67ed" --law-name="Constituição Federal Brasileira de 1988, 67a edição" --s3-key="legislation/br-CF88_67ed.pdf" --wait
python scripts/legislation_cli.py ingest-legislation --law-id="br-codigo-civil" --law-name="Código Civil Brasileiro" --s3-key="legislation/br-codigo-civil-2a-ed.pdf" --wait
python scripts/legislation_cli.py ingest-legislation --law-id="br-cdc" --law-name="Código de Defesa do Consumidor" --s3-key="legislation/br-CDC_2025.pdf" --wait
python scripts/legislation_cli.py ingest-legislation --law-id="mx-codigo-civil-federal" --law-name="Código Civil Federal de México" --s3-key="legislation/mx-codigo-civil-federal.pdf" --wait
```

**Data Retention:** Legislation files in S3 have no expiration policy (kept indefinitely). Deleting files from S3 does not automatically remove them from the Knowledge Base - you must trigger a [data source sync](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-data-source-sync-ingest.html) to reflect deletions.

**File Size Limits:** PDF files must not exceed 50 MB per document. See [Knowledge Base data prerequisites](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-ds.html) for details.

## Development

### Running Tests

The project uses pytest for testing. To run the test suite:

1. Ensure your virtual environment is activated:
```shell
source .venv/bin/activate
```

2. Install development dependencies:
```shell
pip install -r requirements-dev.txt
```

3. Run all tests:
```shell
python -m pytest tests/ -v
```

4. Run tests by directory:
```shell
python -m pytest tests/unit/ -v          # Unit tests only
python -m pytest tests/integration/ -v   # Integration tests only
```

5. Run with coverage:
```shell
pytest tests/ --cov=stack --cov-report=html
```

Test results can be redirected to a file for review:
```shell
python -m pytest tests/ -v > /tmp/pytest_output.txt 2>&1
```

### Token Usage Tracking

Track LLM token consumption for guideline compliance workflow executions.

**Note**: Currently supports the guideline compliance workflow only. Does not yet track legislation check or contract import workflows.

```bash
# Query specific job token usage
python scripts/workflow_token_usage.py --job-id <job-id>

# Query all token usage in last 24 hours
python scripts/workflow_token_usage.py --hours 24
```
