# Code Expert Demo App

A UI [Streamlit](https://streamlit.io/) application is include to demonstrate Code Expert.

> Please note that the application is intended solely for demonstration. It should not be used in a production
> environment.

## Requirements

You need the following to run the application:

- Code Expert deployed in your AWS account.
- AWS Credentials configured in your environment. Refer
  to [Configuration and credential file settings](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html).
- Python configured (tested with version 3.12.2).

## Running the application

To run the application, execute the command below (replace `STEPFUNCTIONS_ARN` with the ARN of your StepFunctions state
machine, `INPUT_S3_BUCKET` with the S3 bucket name, and `RULES_FILE` with the path to the rules JSON file):

```shell
poetry run streamlit run app.py STEPFUNCTIONS_ARN INPUT_S3_BUCKET RULES_FILE
```

The application should appear in a new tab in your web browser.
