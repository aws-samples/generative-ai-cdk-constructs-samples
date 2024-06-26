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

export type Job = {
  id: string;
  filename: string;
  status: "RUNNING" | "SUCCEEDED" | "FAILED" | "TIMED_OUT" | "ABORTED";
  needs_review: boolean;
  start_date: string;
  end_date: string;
};

export type ComplianceStatus = "compliant" | "missing" | "non_compliant";
export type ImpactLevel = "low" | "medium" | "high";
export type RiskLevel = "none" | "low" | "medium" | "high";

export type ComplianceStatusData = {
  quantity: number;
  risk: RiskLevel;
};

export type ComplianceData = Record<ComplianceStatus, ComplianceStatusData>;

export type ClauseTypesByRisk = Record<
  RiskLevel,
  {
    threshold?: number;
    quantity: number;
  }
>;

export type TotalComplianceByImpact = Record<ImpactLevel, ComplianceData>;

export interface ApiResponse {
  id: string;
  document_s3_path: string;
  total_compliance_by_impact: TotalComplianceByImpact;
  total_clause_types_by_risk: ClauseTypesByRisk;
  needs_review: boolean;
  unknown_total: number;
}
