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

const env = import.meta.env;

Amplify.configure(
  {
    Auth: {
      Cognito: {
        userPoolId: env.VITE_COGNITO_USER_POOL_ID,
        userPoolClientId: env.VITE_COGNITO_USER_POOL_CLIENT_ID,
        identityPoolId: env.VITE_COGNITO_IDENTITY_POOL_ID,
      },
    },
    API: {
      REST: {
        [env.VITE_API_NAME]: {
          endpoint: env.VITE_API_GATEWAY_REST_ENDPOINT,
          region: env.VITE_AWS_REGION,
        },
      },
    },
    Storage: {
      S3: {
        region: env.VITE_AWS_REGION,
        bucket: env.VITE_S3_BUCKET_NAME,
      },
    },
  },
  {
    API: {
      REST: {
        headers: async () => ({
          Authorization: (
            await fetchAuthSession()
          ).tokens?.idToken?.toString() as string,
        }),
      },
    },
  },
);
