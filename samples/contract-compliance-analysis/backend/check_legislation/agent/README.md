# Legislation Agent

AI-powered agent service for contract analysis using Amazon Bedrock and Strands Agents framework.

## Overview

This containerized agent service provides:
- Intelligent contract clause analysis
- AI-powered legal document processing
- Integration with legal knowledge bases

## Features

- Bedrock Knowledge Base integration
- Integrated Evals (comming soon!)
- Multiple Multi-Agent Architectures (comming soon!)

## Development

### Prerequisites

- Python 3.13+
- Docker (for containerized deployment)

### Setup

1. Create virtual environment and install dependencies using pip:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run agent locally:

You must have deployed the infrastructure first, in order to get the Knowledge Base ID, or manually create your own.

```bash
LOG_LEVEL=INFO KNOWLEDGE_BASE_ID=XXXXXX python entrypoint.py

INFO:     Started server process [57932]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8080 (Press CTRL+C to quit)
```

To run locally with a mock clauses database table, you can run:

```bash
LOG_LEVEL=INFO TEST_LOCAL=1 KNOWLEDGE_BASE_ID=XXXXXX python entrypoint.py
```

### Run with Docker (emulate AgentCore)

You can also run the agent as will AgentCore. Make sure you create a .env file with AWS credentials, see `.env.example`.

```bash
cd check_legislation/agent
docker build -t legislation-agent .
docker run --env-file=.env -p 8080:8080 --entrypoint=python legislation-agent -m entrypoint
```

Then you can invoke your agent from the outside by making a curl request to:

```bash
curl http://localhost:8080/ping

curl -X POST http://localhost:8080/invocations -H "Content-type: application/json" -d @example_payload.json
```

## Agent Types

- **Single Agent** - Individual contract analysis tasks
- **Graph Agent** - Complex workflow orchestration (comming soon!)

## Components

### Agents
- `single_agent.py` - Individual task processing

### Tools
- `bedrock_knowledge_base.py` - Knowledge base integration

### Repository
- `dynamodb_clause_repository.py` - DynamoDB clauses storage

## Environment Variables

- `LOG_LEVEL` - Log level
- `KNOWLEDGE_BASE_ID` - Bedrock Knowledge Base ID
- `BEDROCK_XACCT_ROLE` - You can pass a cross account role that will be assumed to invoke bedrock. Can be used for better quotas.

## Testing

WIP

Run tests with:
```bash
pytest -v
```

## Evaluation

COMMING SOON!

Use the evaluation framework in `evals/` to test agent performance and accuracy.
