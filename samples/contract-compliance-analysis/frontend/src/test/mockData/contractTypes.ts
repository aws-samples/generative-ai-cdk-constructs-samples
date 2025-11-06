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

import type { ContractType } from "@/lib/types";

/**
 * Mock contract type for UI testing
 * Used by mock jobs to ensure filter consistency
 */
export const MOCK_CONTRACT_TYPE: ContractType = {
  contractTypeId: "mock-contract",
  name: "Mock Contract",
  description: "Contract type for UI testing and validation",
  companyPartyType: "Company",
  otherPartyType: "Third Party",
  highRiskThreshold: 70,
  mediumRiskThreshold: 50,
  lowRiskThreshold: 30,
  isActive: true,
  defaultLanguage: "en",
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};
