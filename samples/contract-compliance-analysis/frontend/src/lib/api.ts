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
import { get, post } from "aws-amplify/api";
import axios from "axios";
import { getErrorMessage } from "./utils";

const env = import.meta.env;

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

const defaultRestInput = {
  apiName: env.VITE_API_NAME,
  options: {
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
  },
};

export async function getJobs() {
  try {
    const restOperation = get({
      ...defaultRestInput,
      path: "/jobs",
    });
    const response = await restOperation.response;
    return response.body.json();
  } catch (e: unknown) {
    console.log("GET call failed: ", getErrorMessage(e));
  }
}

export async function getJob(jobId: string) {
  try {
    const restOperation = get({
      ...defaultRestInput,
      path: `/jobs/${jobId}`,
    });
    const response = await restOperation.response;
    return response.body.json();
  } catch (e: unknown) {
    console.log("GET call failed: ", getErrorMessage(e));
  }
}

export async function uploadDocument(file: File | Blob, filename: string) {
  try {
    const upload = await axios({
      method: "PUT",
      url: `${env.VITE_API_GATEWAY_REST_API_ENDPOINT}/documents/${filename}`,
      data: file,
      headers: {
        Authorization: `Bearer ${authToken}`,
        "Content-Type": "text/plain",
      },
    });

    return upload;
  } catch (e: unknown) {
    console.log("PUT call failed: ", getErrorMessage(e));
  }
}

export async function getDocument(filename: string) {
  try {
    const restOperation = get({
      ...defaultRestInput,
      path: `/documents/${filename}`,
    });
    const response = await restOperation.response;
    return response;
  } catch (e: unknown) {
    console.log("GET call failed: ", getErrorMessage(e));
  }
}

export async function createJob(filename: string) {
  try {
    const restOperation = post({
      ...defaultRestInput,
      path: `/jobs`,
      options: {
        ...defaultRestInput.options,
        body: {
          filename: filename,
        },
      },
    });
    const response = await restOperation.response;
    return response.body.json();
  } catch (e: unknown) {
    console.log("POST call failed: ", getErrorMessage(e));
  }
}
