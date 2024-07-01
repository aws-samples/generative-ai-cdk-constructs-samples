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

import { Amplify, API, Auth } from "aws-amplify";
import axios from "axios";

const env = import.meta.env;

Amplify.configure({
  Auth: {
    region: env.VITE_REGION_NAME,
    userPoolId: env.VITE_COGNITO_USER_POOL_ID,
    userPoolWebClientId: env.VITE_COGNITO_USER_POOL_CLIENT_ID,
    identityPoolId: env.VITE_COGNITO_IDENTITY_POOL_ID,
  },
  API: {
    endpoints: [
      {
        name: env.VITE_API_GATEWAY_REST_API_NAME,
        endpoint: env.VITE_API_GATEWAY_REST_API_ENDPOINT,
        custom_header: async () => {
          return {
            Authorization: `Bearer ${(await Auth.currentSession())
              .getIdToken()
              .getJwtToken()}`,
          };
        },
      },
    ],
  },
});

export async function getJobs() {
  const call = await API.get(env.VITE_API_GATEWAY_REST_API_NAME, `jobs`, {
    response: true,
  });

  return call.data;
}

export async function getJob(jobId?: string) {
  const call = await API.get(
    env.VITE_API_GATEWAY_REST_API_NAME,
    `jobs/${jobId}`,
    {
      response: true,
    },
  );

  return call.data;
}

export async function uploadDocument(file: File | Blob, filename: string) {
  const upload = await axios({
    method: "PUT",
    url: `${await API.endpoint(
      env.VITE_API_GATEWAY_REST_API_NAME,
    )}/documents/${filename}`,
    data: file,
    headers: {
      Authorization: `Bearer ${(await Auth.currentSession())
        .getIdToken()
        .getJwtToken()}`,
      "Content-Type": "text/plain",
    },
  });

  return upload;
}

export async function getDocument(filename: string) {
  const call = await API.get(
    env.VITE_API_GATEWAY_REST_API_NAME,
    `documents/${filename}`,
    {
      response: true,
    },
  );

  return call.data;
}

export async function createJob(filename: string) {
  const call = await API.post(env.VITE_API_GATEWAY_REST_API_NAME, `jobs`, {
    body: {
      filename: filename,
    },
  });

  return call.data;
}
