# Contract Compliance Analysis - Setup Guide

This guide covers the key steps to deploy and run the Contract Compliance Analysis prototype.

## Follow READMEs in order (please read each one in full)
1. `backend/README.md` - Deploy backend stack and load guidelines
2. `frontend/README.md` - Configure and run frontend

## What to check before starting the deployment
- Check if there is AWS profile configure
- Check the AWS account number and ask user to confirm it's the expected one
- Get AWS default account region and ask user to confirm it's the expected one

## General deployment/configuration recommendations
- Follow README instructions in sequence. Make sure not to miss instructions.
- For running `cdk deploy`, `cdk bootstrap` or any other command that will log much content, run the command redirecting the log to a temporary folder
- It's recommended to run cdk deploy having '--require-approval=never' flag, otherwise cdk deploy will prompt for typing (y/n) but the user will not see, since it's running behind q chat / execute_bash
- Legislation Check is an optional feature, but feel free to ask user if they want the feature to be configured - but alert about the costs (OpenSearch)
- For frontend, rather than running the command to start the web application, just tell the user what the command is

## Additional Steps for MainBackendStack stack

### 1. Enable Bedrock Model Access
Follow the "Enable Bedrock Model Access (Prerequisite)" section in `backend/README.md` before deploying the stack.

### 2. Get Stack Outputs for Frontend
```bash
aws cloudformation describe-stacks --stack-name MainBackendStack --query "Stacks[0].Outputs"
```

### 3. Create Cognito User
Follow the "Add users to Cognito User Pool" section in `backend/README.md`
