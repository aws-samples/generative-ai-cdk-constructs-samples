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

import type { Clause, ClauseType, ImpactLevel } from "@/lib/types";
import { mockFaker } from "./faker.config";

/**
 * Generate mock clauses based on job compliance characteristics
 */
export function generateClausesForJob(
  _jobId: string,
  compliance: {
    hasGuidelinesIssues: boolean;
    hasLegislationIssues: boolean;
    isFullyCompliant: boolean;
  },
): Clause[] {
  const { hasGuidelinesIssues, hasLegislationIssues, isFullyCompliant } =
    compliance;

  // Simple implementation: 2-3 clauses per job
  const clauseCount = 3;
  const clauses: Clause[] = [];

  for (let i = 0; i < clauseCount; i++) {
    const clauseNumber = (i + 1).toString();
    const clauseType = mockFaker.clauseType();

    // Determine clause compliance based on job status
    let guidelinesCompliant = true;
    let legislationCompliant = true;

    if (!isFullyCompliant) {
      // For non-compliant jobs, make some clauses non-compliant
      if (hasGuidelinesIssues && i === 0) {
        guidelinesCompliant = false;
      }
      if (hasLegislationIssues && i === 1) {
        legislationCompliant = false;
      }
    }

    const impactLevel: ImpactLevel =
      i === 0 ? "high" : i === 1 ? "medium" : "low";

    const clauseTypes: ClauseType[] = [
      {
        typeName: clauseType.typeName,
        typeId: clauseType.typeId,
        analysis: mockFaker.complianceAnalysis(guidelinesCompliant),
        classificationAnalysis: `This clause has been classified as ${clauseType.typeName} based on its content and structure.`,
        compliant: guidelinesCompliant,
        level: impactLevel,
      },
    ];

    const clause: Clause = {
      text: mockFaker.clauseText(),
      clause_number: clauseNumber,
      types: clauseTypes,
      // Add legislation check if job has legislation
      ...(hasLegislationIssues !== undefined && {
        additionalChecks: {
          legislationCheck: {
            compliant: legislationCompliant,
            analysis: legislationCompliant
              ? "This clause complies with applicable legislation."
              : "This clause may not fully comply with current legislative requirements.",
          },
        },
      }),
    };

    clauses.push(clause);
  }

  return clauses;
}
