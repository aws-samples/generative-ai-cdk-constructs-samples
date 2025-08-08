# Contract Compliance Analysis - Front-end

Welcome to the demo front-end application. With this, you'll be able to upload and review contracts processed by the back-end application.


## Technologies

- React + Typescript (through Vite)
- Amplify UI (authentication flow)
- TailwindCSS (styling)
- shadcn/ui (custom components)

## Prerequisites

- Node/npm
- The deployed back-end.
- At least one user added on the appropriate Amazon Cognito User Pool (required for authenticated API calls).

## Setup and run

1. After successfully deploying your back-end stack, you can easily find the information required for the next step by inspecting to Amazon API Gateway and/or Amazon CloudFormation console.

2. Create a `.env` file by duplicating the included `example.env` and replace the property values with the values retrieved from MainBackendStack outputs.

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

4. Start web application
   ```shell
   $ npm run dev
   ```

A url like `http://localhost:5173/` will be displayed, so you can open the web application from your browser 

## How to analyze a contract

Once you open the web application in your browser, click the **Browse** button near the top right corner and select a contract file. The file needs to be in plain text format.  

![Main page](images/main-webapp-page.png)

For ready-to-use examples, refer to the **back-end/samples** folder.

Once the file is selected, the contract analysis processing task starts and a new entry is added to the page. 

The processing will take a couple of minutes. A click to the refresh button displays the current status of all processing tasks.


## Warning about hosting

It is definitely recommended to perform a thorough security testing, including pen-tests, before hosting this Front-end 
application publicly. The work is provided “AS IS” without warranties or conditions of any kind, either express or 
implied, including warranties or conditions of merchantability.

