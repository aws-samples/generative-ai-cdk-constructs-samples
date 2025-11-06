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

import type {
  Clause,
  TotalComplianceByImpact,
  ClauseTypesByRisk,
  ImpactLevel,
  RiskLevel,
} from "@/lib/types";

/**
 * Calculate job-level metrics from generated clauses
 */
export function calculateJobMetrics(clauses: Clause[]) {
  const totalComplianceByImpact = calculateComplianceByImpact(clauses);
  const totalClauseTypesByRisk = calculateClauseTypesByRisk(clauses);
  const unknownTotal = calculateUnknownTotal(clauses);

  return {
    totalComplianceByImpact,
    totalClauseTypesByRisk,
    unknownTotal,
  };
}

/**
 * Calculate compliance distribution by impact level
 */
function calculateComplianceByImpact(
  clauses: Clause[],
): TotalComplianceByImpact {
  const metrics: TotalComplianceByImpact = {
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

  clauses.forEach((clause) => {
    clause.types.forEach((type) => {
      const level = type.level as ImpactLevel;
      if (type.compliant) {
        metrics[level].compliant.quantity++;
      } else {
        metrics[level].non_compliant.quantity++;
      }
    });
  });

  return metrics;
}

/**
 * Calculate clause types distribution by risk level
 */
function calculateClauseTypesByRisk(clauses: Clause[]): ClauseTypesByRisk {
  const metrics: ClauseTypesByRisk = {
    none: { quantity: 0 },
    low: { quantity: 0 },
    medium: { quantity: 0 },
    high: { quantity: 0 },
  };

  // For mock purposes, assume most clauses are "none" risk since they're compliant
  // In real implementation, this would be calculated based on actual risk assessment
  clauses.forEach((clause) => {
    clause.types.forEach((type) => {
      if (type.compliant) {
        metrics.none.quantity++;
      } else {
        // Non-compliant clauses get distributed based on their impact level
        const riskLevel: RiskLevel =
          type.level === "high"
            ? "high"
            : type.level === "medium"
              ? "medium"
              : "low";
        metrics[riskLevel].quantity++;
      }
    });
  });

  return metrics;
}

/**
 * Calculate unknown clauses total
 */
function calculateUnknownTotal(clauses: Clause[]): number {
  return clauses.filter((clause) =>
    clause.types.some((type) => type.typeId === "UNKNOWN"),
  ).length;
}
