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

import "@lib/amplify"; // Import this first so auth is validated before other calls.

import React from "react";
import ReactDOM from "react-dom/client";
import { Authenticator } from "@aws-amplify/ui-react";
import { RouterProvider, createBrowserRouter } from "react-router";
import { Root, Errors, Home, Jobs, ContractTypeGuidelines } from "@/routes";
import { ContractTypeManagement } from "@/components/ContractTypeManagement";
import "@/styles/index.css";
import { Toaster } from "@/components/ui/sonner";

const router = createBrowserRouter([
  {
    path: "/",
    element: <Root />,
    errorElement: <Errors />,
    children: [
      { index: true, element: <Home /> },
      { path: "jobs/:jobId", element: <Jobs /> },
      { path: "contract-types", element: <ContractTypeManagement /> },
      {
        path: "contract-types/:contractTypeId/guidelines",
        element: <ContractTypeGuidelines />,
      },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Authenticator.Provider>
      <Authenticator hideSignUp={true}>
        <RouterProvider router={router} />
        <Toaster />
      </Authenticator>
    </Authenticator.Provider>
  </React.StrictMode>,
);
