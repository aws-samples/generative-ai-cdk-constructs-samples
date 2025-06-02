//
// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
// with the License. A copy of the License is located at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
// OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
// and limitations under the License.
//

import { Amplify } from "aws-amplify";
import { fetchAuthSession } from "aws-amplify/auth";
import { getErrorMessage } from "./utils";

// Get the environment variables from the window object or the import.meta.env object
// Window object is set by the custom resource in the backend stack
// If the window object is not set, use the import.meta.env object (local development)
const env = window.APP_CONFIG || import.meta.env;

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: env.VITE_COGNITO_USER_POOL_ID,
      userPoolClientId: env.VITE_COGNITO_USER_POOL_CLIENT_ID,
      identityPoolId: env.VITE_COGNITO_IDENTITY_POOL_ID,
    },
  },
});

const existingConfig = Amplify.getConfig();

Amplify.configure({
  ...existingConfig,
  API: {
    REST: {
      [env.VITE_API_NAME]: {
        endpoint: env.VITE_API_GATEWAY_REST_API_ENDPOINT,
        region: env.VITE_AWS_REGION,
      },
    },
  },
});

const authToken = (await fetchAuthSession()).tokens?.idToken?.toString();

interface QARequest {
  jobId: string;
  model: string;
  question: string;
}

export async function askQuestion(data: QARequest): Promise<Response> {
  try {
    const response = await fetch(`${env.VITE_API_GATEWAY_REST_API_ENDPOINT}/qa`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`,
      },
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      throw new Error('Failed to get response from Q&A endpoint');
    }

    return response;
  } catch (e: unknown) {
    console.error("Q&A request failed:", getErrorMessage(e));
    throw e;
  }
}