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

import type { Job } from "@/lib/types";
import { MOCK_CONTRACT_TYPE } from "./contractTypes";
import { generateClausesForJob } from "./generators/clauses";
import { calculateJobMetrics } from "./generators/aggregates";

/**
 * Mock job data for UI testing and validation
 * Used when VITE_ENABLE_MOCK_JOBS=true
 */
export function getMockJobsList(): Job[] {
  const now = new Date();
  const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  const twoDaysAgo = new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000);
  const threeDaysAgo = new Date(now.getTime() - 3 * 24 * 60 * 60 * 1000);

  return [
    // 1. RUNNING - Processing job
    {
      id: "mock-job-running-1",
      jobDescription: "Contract analysis in progress",
      documentS3Key: "documents/mock-running-contract.pdf",
      contractTypeId: "mock-contract",
      contractType: MOCK_CONTRACT_TYPE,
      status: "RUNNING",
      needsReview: false,
      startDate: now.toISOString(),
      endDate: "None",
      clauses: [],
      checks: {
        guidelines: {
          compliant: false,
          processingStatus: "RUNNING",
        },
        legislation: {
          compliant: false,
          processingStatus: "RUNNING",
        },
      },
    },

    // 2. SUCCEEDED - Fully compliant contract
    (() => {
      const clauses = generateClausesForJob("mock-job-succeeded-1", {
        hasGuidelinesIssues: false,
        hasLegislationIssues: false,
        isFullyCompliant: true,
      });
      const metrics = calculateJobMetrics(clauses);

      return {
        id: "mock-job-succeeded-1",
        jobDescription: "Fully compliant contract analysis",
        documentS3Key: "documents/mock-compliant-contract.pdf",
        contractTypeId: "mock-contract",
        contractType: MOCK_CONTRACT_TYPE,
        status: "SUCCEEDED",
        needsReview: false,
        startDate: yesterday.toISOString(),
        endDate: yesterday.toISOString(),
        clauses,
        ...metrics,
        checks: {
          guidelines: {
            compliant: true,
            processingStatus: "SUCCEEDED",
            metrics,
          },
          legislation: {
            compliant: true,
            processingStatus: "SUCCEEDED",
          },
        },
      };
    })(),

    // 3. SUCCEEDED - Contract with compliance issues
    (() => {
      const clauses = generateClausesForJob("mock-job-succeeded-2", {
        hasGuidelinesIssues: true,
        hasLegislationIssues: true,
        isFullyCompliant: false,
      });
      const metrics = calculateJobMetrics(clauses);

      return {
        id: "mock-job-succeeded-2",
        jobDescription: "Contract with compliance issues",
        documentS3Key: "documents/mock-non-compliant-contract.pdf",
        contractTypeId: "mock-contract",
        contractType: MOCK_CONTRACT_TYPE,
        status: "SUCCEEDED",
        needsReview: true,
        startDate: twoDaysAgo.toISOString(),
        endDate: twoDaysAgo.toISOString(),
        clauses,
        ...metrics,
        checks: {
          guidelines: {
            compliant: false,
            processingStatus: "SUCCEEDED",
            metrics,
          },
          legislation: {
            compliant: false,
            processingStatus: "SUCCEEDED",
          },
        },
      };
    })(),

    // 4. FAILED - Analysis that failed
    {
      id: "mock-job-failed-1",
      jobDescription: "Analysis that failed to complete",
      documentS3Key: "documents/mock-failed-contract.pdf",
      contractTypeId: "mock-contract",
      contractType: MOCK_CONTRACT_TYPE,
      status: "FAILED",
      needsReview: false,
      startDate: threeDaysAgo.toISOString(),
      endDate: threeDaysAgo.toISOString(),
      clauses: [],
      checks: {
        guidelines: {
          compliant: false,
          processingStatus: "FAILED",
        },
        legislation: {
          compliant: false,
          processingStatus: "FAILED",
        },
      },
    },

    // 5. TIMED_OUT - Analysis that timed out
    {
      id: "mock-job-timedout-1",
      jobDescription: "Analysis that timed out",
      documentS3Key: "documents/mock-timedout-contract.pdf",
      contractTypeId: "mock-contract",
      contractType: MOCK_CONTRACT_TYPE,
      status: "TIMED_OUT",
      needsReview: false,
      startDate: threeDaysAgo.toISOString(),
      endDate: threeDaysAgo.toISOString(),
      clauses: [],
      checks: {
        guidelines: {
          compliant: false,
          processingStatus: "TIMED_OUT",
        },
        legislation: {
          compliant: false,
          processingStatus: "TIMED_OUT",
        },
      },
    },

    // 6. ABORTED - Cancelled analysis
    {
      id: "mock-job-aborted-1",
      jobDescription: "Cancelled contract analysis",
      documentS3Key: "documents/mock-aborted-contract.pdf",
      contractTypeId: "mock-contract",
      contractType: MOCK_CONTRACT_TYPE,
      status: "ABORTED",
      needsReview: false,
      startDate: threeDaysAgo.toISOString(),
      endDate: threeDaysAgo.toISOString(),
      clauses: [],
      checks: {
        guidelines: {
          compliant: false,
          processingStatus: "ABORTED",
        },
        legislation: {
          compliant: false,
          processingStatus: "ABORTED",
        },
      },
    },

    // 7. SUCCEEDED - Guidelines passed but legislation failed
    (() => {
      const clauses = generateClausesForJob("mock-job-mixed-1", {
        hasGuidelinesIssues: false,
        hasLegislationIssues: true,
        isFullyCompliant: false,
      });
      const metrics = calculateJobMetrics(clauses);

      return {
        id: "mock-job-mixed-1",
        jobDescription: "Guidelines passed, legislation failed",
        documentS3Key: "documents/mock-mixed-status-contract.pdf",
        contractTypeId: "mock-contract",
        contractType: MOCK_CONTRACT_TYPE,
        status: "SUCCEEDED",
        needsReview: true,
        startDate: twoDaysAgo.toISOString(),
        endDate: twoDaysAgo.toISOString(),
        clauses,
        ...metrics,
        checks: {
          guidelines: {
            compliant: true,
            processingStatus: "SUCCEEDED",
            metrics,
          },
          legislation: {
            compliant: false,
            processingStatus: "FAILED",
          },
        },
      };
    })(),

    // 8. RUNNING - Guidelines completed, legislation processing
    {
      id: "mock-job-partial-running-1",
      jobDescription: "Guidelines completed, legislation processing",
      documentS3Key: "documents/mock-partial-running-contract.pdf",
      contractTypeId: "mock-contract",
      contractType: MOCK_CONTRACT_TYPE,
      status: "RUNNING",
      needsReview: false,
      startDate: now.toISOString(),
      endDate: "None",
      clauses: [],
      checks: {
        guidelines: {
          compliant: true,
          processingStatus: "SUCCEEDED",
        },
        legislation: {
          compliant: false,
          processingStatus: "RUNNING",
        },
      },
    },

    // 9. FAILED - Guidelines failed but legislation passed
    {
      id: "mock-job-guidelines-failed-legislation-pass",
      jobDescription: "Guidelines failed, legislation passed",
      documentS3Key: "documents/mock-guidelines-failed-legislation-pass.pdf",
      contractTypeId: "mock-contract",
      contractType: MOCK_CONTRACT_TYPE,
      status: "FAILED",
      needsReview: true,
      startDate: threeDaysAgo.toISOString(),
      endDate: threeDaysAgo.toISOString(),
      clauses: [],
      checks: {
        guidelines: {
          compliant: false,
          processingStatus: "FAILED",
        },
        legislation: {
          compliant: true,
          processingStatus: "SUCCEEDED",
        },
      },
    },

    // 10. SUCCEEDED - Guidelines passed, legislation non-compliant
    (() => {
      const clauses = generateClausesForJob(
        "mock-job-guidelines-ok-legislation-noncompliant",
        {
          hasGuidelinesIssues: false,
          hasLegislationIssues: true,
          isFullyCompliant: false,
        },
      );
      const metrics = calculateJobMetrics(clauses);

      return {
        id: "mock-job-guidelines-ok-legislation-noncompliant",
        jobDescription: "Guidelines passed, legislation non-compliant",
        documentS3Key:
          "documents/mock-guidelines-ok-legislation-noncompliant.pdf",
        contractTypeId: "mock-contract",
        contractType: MOCK_CONTRACT_TYPE,
        status: "SUCCEEDED",
        needsReview: true,
        startDate: twoDaysAgo.toISOString(),
        endDate: twoDaysAgo.toISOString(),
        clauses,
        ...metrics,
        checks: {
          guidelines: {
            compliant: true,
            processingStatus: "SUCCEEDED",
            metrics,
          },
          legislation: {
            compliant: false,
            processingStatus: "SUCCEEDED",
          },
        },
      };
    })(),

    // 11. SUCCEEDED - Guidelines non-compliant, legislation passed
    (() => {
      const clauses = generateClausesForJob(
        "mock-job-guidelines-noncompliant-legislation-ok",
        {
          hasGuidelinesIssues: true,
          hasLegislationIssues: false,
          isFullyCompliant: false,
        },
      );
      const metrics = calculateJobMetrics(clauses);

      return {
        id: "mock-job-guidelines-noncompliant-legislation-ok",
        jobDescription: "Guidelines non-compliant, legislation passed",
        documentS3Key:
          "documents/mock-guidelines-noncompliant-legislation-ok.pdf",
        contractTypeId: "mock-contract",
        contractType: MOCK_CONTRACT_TYPE,
        status: "SUCCEEDED",
        needsReview: true,
        startDate: yesterday.toISOString(),
        endDate: yesterday.toISOString(),
        clauses,
        ...metrics,
        checks: {
          guidelines: {
            compliant: false,
            processingStatus: "SUCCEEDED",
            metrics,
          },
          legislation: {
            compliant: true,
            processingStatus: "SUCCEEDED",
          },
        },
      };
    })(),

    // 12. SUCCEEDED - Guidelines only, compliant
    (() => {
      const clauses = generateClausesForJob(
        "mock-job-no-legislation-compliant",
        {
          hasGuidelinesIssues: false,
          hasLegislationIssues: false,
          isFullyCompliant: true,
        },
      );
      const metrics = calculateJobMetrics(clauses);

      return {
        id: "mock-job-no-legislation-compliant",
        jobDescription: "Guidelines only analysis - compliant",
        documentS3Key: "documents/mock-no-legislation-compliant.pdf",
        contractTypeId: "mock-contract",
        contractType: MOCK_CONTRACT_TYPE,
        status: "SUCCEEDED",
        needsReview: false,
        startDate: yesterday.toISOString(),
        endDate: yesterday.toISOString(),
        clauses,
        ...metrics,
        checks: {
          guidelines: {
            compliant: true,
            processingStatus: "SUCCEEDED",
            metrics,
          },
        },
      };
    })(),

    // 13. SUCCEEDED - Guidelines only, non-compliant
    (() => {
      const clauses = generateClausesForJob(
        "mock-job-no-legislation-noncompliant",
        {
          hasGuidelinesIssues: true,
          hasLegislationIssues: false,
          isFullyCompliant: false,
        },
      );
      const metrics = calculateJobMetrics(clauses);

      return {
        id: "mock-job-no-legislation-noncompliant",
        jobDescription: "Guidelines only analysis - non-compliant",
        documentS3Key: "documents/mock-no-legislation-noncompliant.pdf",
        contractTypeId: "mock-contract",
        contractType: MOCK_CONTRACT_TYPE,
        status: "SUCCEEDED",
        needsReview: true,
        startDate: twoDaysAgo.toISOString(),
        endDate: twoDaysAgo.toISOString(),
        clauses,
        ...metrics,
        checks: {
          guidelines: {
            compliant: false,
            processingStatus: "SUCCEEDED",
            metrics,
          },
        },
      };
    })(),

    // 14. FAILED - Guidelines only, failed
    {
      id: "mock-job-no-legislation-failed",
      jobDescription: "Guidelines only analysis - failed",
      documentS3Key: "documents/mock-no-legislation-failed.pdf",
      contractTypeId: "mock-contract",
      contractType: MOCK_CONTRACT_TYPE,
      status: "FAILED",
      needsReview: false,
      startDate: threeDaysAgo.toISOString(),
      endDate: threeDaysAgo.toISOString(),
      clauses: [],
      checks: {
        guidelines: {
          compliant: false,
          processingStatus: "FAILED",
        },
      },
    },
  ];
}

/**
 * Get mock job by ID for individual job queries
 */
export function getMockJobById(jobId: string): Job | undefined {
  const mockJobs = getMockJobsList();
  return mockJobs.find((job) => job.id === jobId);
}
