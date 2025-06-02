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

import { Authenticator } from "@aws-amplify/ui-react";
import "@aws-amplify/ui-react/styles.css";
import { Amplify } from "aws-amplify";
import React from "react";
import ReactDOM from "react-dom/client";
import {
  Route,
  RouterProvider,
  createBrowserRouter,
  createRoutesFromElements,
} from "react-router-dom";

import "./index.css";

import Error from "@/routes/Errors";
import { RequireAuth } from "./components/RequireAuth";
import { Login } from "./routes/Login";
import Root from "@/routes/Root";
import Introduction from "./routes/Introduction";
import SpeechToSpeechPage from "./routes/SpeechToSpeechPage";

// Get the environment variables from the window object or the import.meta.env object
// Window object is set by the custom resource in the backend stack
// If the window object is not set, use the import.meta.env object (local development)
const env = window.APP_CONFIG || import.meta.env;

// Configure Amplify
Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: env.VITE_COGNITO_USER_POOL_ID,
      userPoolClientId: env.VITE_COGNITO_USER_POOL_CLIENT_ID,
      identityPoolId: env.VITE_COGNITO_IDENTITY_POOL_ID,
    },
  },
});

const router = createBrowserRouter(
  createRoutesFromElements(
    <Route errorElement={<Error />}>
      <Route
        element={
          <RequireAuth>
            <Root />
          </RequireAuth>
        }
      >
        <Route index element={<SpeechToSpeechPage />} />
        <Route path="introduction" element={<Introduction />} />
      </Route>
      <Route path="login" element={<Login />} />
    </Route>,
  ),
);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Authenticator.Provider>
      <RouterProvider router={router} />
    </Authenticator.Provider>
  </React.StrictMode>,
);