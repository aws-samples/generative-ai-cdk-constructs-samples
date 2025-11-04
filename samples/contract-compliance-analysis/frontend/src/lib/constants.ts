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

import {
  ComplianceStatus,
  RiskLevel,
  ImpactLevel,
  TotalComplianceByImpact,
} from "@/lib/types";

export const IMPACT_LEVELS: Record<ImpactLevel, string> = {
  low: "Low impact",
  medium: "Medium impact",
  high: "High impact",
};

export const IMPACT_COLORS: Record<ImpactLevel, string> = {
  low: "bg-slate-200 text-slate-900 hover:bg-slate-200",
  medium: "bg-slate-300 text-slate-900 hover:bg-slate-300",
  high: "bg-slate-500 text-slate-50 hover:bg-slate-500",
};

export const COMPLIANCE_STATUSES: Record<ComplianceStatus, string> = {
  compliant: "Compliant",
  non_compliant: "Non-compliant",
  missing: "Missing",
};

export const RISK_LEVELS: Record<RiskLevel, string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
  none: "No Risk",
};

export const RISK_COLORS: Record<RiskLevel, string> = {
  none: "bg-slate-100 text-slate-600",
  low: "bg-amber-100 text-amber-900",
  medium: "bg-orange-100 text-orange-900",
  high: "bg-red-200 text-red-950",
};

export const EMPTY_TOTALS: TotalComplianceByImpact = {
  low: {
    compliant: { quantity: 0, risk: "none" },
    missing: { quantity: 0, risk: "none" },
    non_compliant: { quantity: 0, risk: "none" },
  },
  medium: {
    compliant: { quantity: 0, risk: "none" },
    missing: { quantity: 0, risk: "none" },
    non_compliant: { quantity: 0, risk: "none" },
  },
  high: {
    compliant: { quantity: 0, risk: "none" },
    missing: { quantity: 0, risk: "none" },
    non_compliant: { quantity: 0, risk: "none" },
  },
};
