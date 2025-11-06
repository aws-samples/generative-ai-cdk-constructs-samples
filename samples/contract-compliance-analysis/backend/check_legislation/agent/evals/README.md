# Legislation Agent Evaluation

This directory contains promptfoo evaluation setup for the legislation checking agent.

## Setup

Install Python dependencies (if not already done):
   ```bash
   cd ../
   pip install -r requirements.txt
   ```

## Running Evaluations

### Run agent locally

You must run the agent locally so that the evaluation script has an endpoint to connect to.

You must run with the `TEST_LOCAL=1` ENV var such that the agent loads the test_cases.csv file into the Clauses 
repository and for it to return annotated responses which include the compliance and analysis results from the agent.

You will need an Amazon Knowledge Base ID, this is the knowledge base that was deployed in the 
`CheckLegislationAgentStack`. Use the `KNOWLEDGE_BASE_ID=xxxx` to provide the ID to the agent.

Since the agent is running locally, make sure you have valid AWS credentials, otherwise it will fail to invoke 
llm models.

```bash
LOG_LEVEL=DEBUG KNOWLEDGE_BASE_ID=BUTVJWZXVN TEST_LOCAL=1 python entrypoint.py
INFO:     Started server process [59349]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8080 (Press CTRL+C to quit)
```

### Test Cases

Test cases are stored in `test_cases.csv` which can be edited in any spreadsheet application. The CSV includes:

- **Basic test data**: job_id, clause_number, text, legislation_id
- **Ground truth**: expected_compliant, expected_analysis_rubric
- **Assertions**: Automatic validation of Status, Compliant boolean, and Analysis quality using LLM rubrics

**NOTE** that the llm rubric assertion will not be a success criteria (you will see instances of failed llm-rubrics in
successful test cases in the promptfoo UI).

### CSV Columns

- `job_id`: Test job identifier, can be any value
- `clause_number`: Clause number within the job, must be unique, does not need to be incremental, can be any unique number
- `text`: The contract clause text to analyze
- `legislation_id`: Legislation to check against (e.g., 'cdc')
- `expected_compliant`: Expected boolean result (TRUE/FALSE)
- `expected_analysis_rubric`: Rubric for validating the analysis quality -- note that having a well-crafted rubric is key for the evaluation, even though we are using a powerful model for the LLM judge.
- `__expected1`: Status validation (JavaScript assertion)
- `__expected2`: Compliant boolean validation (JavaScript assertion)
- `__expected3`: Analysis quality validation (LLM rubric assertion)

### Running and seeing the evaluations

```
npx promptfoo@latest eval --no-cache
```

If you would like to use previously cached request-responses, remove the `--no-cache` flag.

To view the results

```
npx promptfoo@latest view
```

Then open the url in your browser.