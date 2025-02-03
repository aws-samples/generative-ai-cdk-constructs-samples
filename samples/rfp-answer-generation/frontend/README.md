# RFP Answering with GenAI - Frontend

## Overview

Use this project to develop a prototype frontend using ReactJS.
You can clone this repository and rename the project directory according to your prototype name.

In order to deploy this project, you need to have installed:

- NodeJS and NPM
- AWS CLI
- Git (if using code repository)

You need to have AWS CLI properly configured with the credentials for your AWS account.

You also need to have the backend stack for your prototype deployed into your account.
Make sure to deploy the frontend using the same configuration option as your backend.

### Local development connected to the backend

1. Run AWS CLI command line tool to get the outputs from the `RFPAnswers-InferenceStack`:

   ```shell
   $ aws cloudformation describe-stacks --stack-name RFPAnswers-InferenceStack --query "Stacks[0].Outputs"
   ```

    You'll get an output like this:
    ```
    [
       {
           "OutputKey": "APIConstructCognitoUserPoolClientIdABCD1234",
           "OutputValue": "abcdefghijklmno1234567890",
           "ExportName": ""RFPAnswers-InferenceStackCognitoUserPoolClientId"
       },
       {
           "OutputKey": "APIConstructCognitoUserPoolIdABCD1234",
           "OutputValue": "us-east-1_abc123456",
           "ExportName": ""RFPAnswers-InferenceStackCognitoUserPoolId"
       },
       {
           "OutputKey": "APIConstructCognitoIdentityPoolIdABCD1234",
           "OutputValue": "us-east-1:aaaaaaaa-bbbb-cccc-dddd-123456789012",
           "ExportName": ""RFPAnswers-InferenceStackCognitoIdentityPoolId"
       },
       {
           "OutputKey": "APIConstructApiGatewayRestApiEndpointABCD1234",
           "OutputValue": "https://abcdefghij.execute-api.us-east-1.amazonaws.com/api/",
           "ExportName": ""RFPAnswers-InferenceStackApiGatewayRestApiEndpoint"
       }
    ]

    ```

2. Create a `.env` file as a copy of `example.env` and replace the property values with the values retrieved from the stack outputs.

   ```properties
   VITE_REGION_NAME="<REGION_NAME>"
   VITE_COGNITO_USER_POOL_ID="<COGNITO_USER_POOL_ID>"
   VITE_COGNITO_USER_POOL_CLIENT_ID="<COGNITO_USER_POOL_CLIENT_ID>"
   VITE_COGNITO_IDENTITY_POOL_ID="<COGNITO_IDENTITY_POOL_ID>"
   VITE_API_GATEWAY_REST_API_ENDPOINT="<API_GATEWAY_REST_API_ENDPOINT>"
   ```

3. Install dependencies:

   ```shell
   $ npm install
   ```

4. Start web application:
   ```shell
   $ npm run dev
   ```

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type aware lint rules:

- Configure the top-level `parserOptions` property like this:

```js
   parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    project: ['./tsconfig.json', './tsconfig.node.json'],
    tsconfigRootDir: __dirname,
   },
```

- Replace `plugin:@typescript-eslint/recommended` to `plugin:@typescript-eslint/recommended-type-checked` or `plugin:@typescript-eslint/strict-type-checked`
- Optionally add `plugin:@typescript-eslint/stylistic-type-checked`
- Install [eslint-plugin-react](https://github.com/jsx-eslint/eslint-plugin-react) and add `plugin:react/recommended` & `plugin:react/jsx-runtime` to the `extends` list
