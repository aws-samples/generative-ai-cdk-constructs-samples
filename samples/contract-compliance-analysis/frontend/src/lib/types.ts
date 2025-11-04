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

export interface ClauseType {
  typeName: string;
  typeId: string;
  analysis: string;
  classificationAnalysis: string;
  compliant: boolean;
  level: string;
}

export interface LegislationCheckResult {
  compliant: boolean;
  analysis?: string;
}

export interface AdditionalChecks {
  legislationCheck?: LegislationCheckResult;
}

export interface Clause {
  text: string;
  clause_number: string;
  types: ClauseType[];
  additionalChecks?: AdditionalChecks;
}

export interface ContractType {
  contractTypeId: string;
  name: string;
  description: string;
  companyPartyType: string;
  otherPartyType: string;
  highRiskThreshold: number;
  mediumRiskThreshold: number;
  lowRiskThreshold: number;
  isActive: boolean;
  defaultLanguage: string;
  createdAt: string;
  updatedAt: string;
  // Import-related fields
  isImported?: boolean;
  importSourceDocument?: string;
}

export type Job = {
  id: string;
  jobDescription: string;
  documentS3Key: string;
  contractTypeId: string;
  contractType?: ContractType;
  status: "RUNNING" | "SUCCEEDED" | "FAILED" | "TIMED_OUT" | "ABORTED";
  needsReview?: boolean;
  startDate: string;
  endDate: string;
  // Optional fields present in detailed Job responses
  totalComplianceByImpact?: TotalComplianceByImpact;
  totalClauseTypesByRisk?: ClauseTypesByRisk;
  unknownTotal?: number;
  clauses?: Clause[];
  checks: ChecksCollection;
};

export type ComplianceStatus = "compliant" | "missing" | "non_compliant";
export type ImpactLevel = "low" | "medium" | "high";
export type RiskLevel = "none" | "low" | "medium" | "high";

export type ComplianceAttributes = {
  quantity: number;
  risk: RiskLevel;
};

export type ComplianceData = Record<ComplianceStatus, ComplianceAttributes>;

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
  totalComplianceByImpact: TotalComplianceByImpact;
  totalClauseTypesByRisk: ClauseTypesByRisk;
  needs_review: boolean;
  unknownTotal: number;
}

// Guidelines-related types
export interface Guideline {
  contractTypeId: string;
  clauseTypeId: string;
  name: string;
  standardWording: string;
  level: ImpactLevel;
  evaluationQuestions: string[];
  examples: string[];
  createdAt?: string;
  updatedAt?: string;
}

export interface GuidelineFormData {
  // clauseTypeId is now auto-generated, so removed from form data
  name: string;
  standardWording: string;
  level: ImpactLevel;
  evaluationQuestions: string[];
  examples: string[];
}

export interface GuidelinesFilters {
  search: string;
  level: string;
  contractTypeId: string;
}

export interface GuidelinesListResponse {
  guidelines: Guideline[];
  lastEvaluatedKey?: string;
  totalCount?: number;
}

// Import-related types
export interface ImportJob {
  importJobId: string;
  contractTypeId?: string;
  status: "processing" | "completed" | "failed";
  progress: number;
  error?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface Legislation {
  id: string;
  subjectMatter: string;
  name: string;
  s3Key?: string;
}

export interface CheckMetrics {
  totalClauseTypesByRisk: ClauseTypesByRisk;
  totalComplianceByImpact: TotalComplianceByImpact;
  unknownTotal: number;
}

export interface CheckType {
  compliant: boolean;
  processingStatus:
    | "SUCCEEDED"
    | "FAILED"
    | "RUNNING"
    | "TIMED_OUT"
    | "ABORTED";
  metrics?: CheckMetrics;
}

export interface ChecksCollection {
  guidelines: CheckType;
  legislation?: CheckType;
}
