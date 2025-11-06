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

import { get, post, put, del } from "aws-amplify/api";
import { fetchAuthSession } from "aws-amplify/auth";
import { getErrorMessage } from "@lib/utils";
import type {
  Job,
  ContractType,
  Guideline,
  GuidelinesListResponse,
  GuidelineFormData,
  Legislation,
} from "@lib/types";
import { getMockJobsList, getMockJobById, isMockJobId } from "@/test/mockData";

const env = import.meta.env;
const apiName = env.VITE_API_NAME;

export async function getJobs(contractTypeId?: string) {
  console.log(
    "Getting jobs",
    contractTypeId ? `for contract type: ${contractTypeId}` : "",
  );
  try {
    // If filtering by mock contract type, return only mock jobs
    if (
      import.meta.env.VITE_ENABLE_MOCK_JOBS === "true" &&
      contractTypeId === "mock-contract"
    ) {
      const mockJobs = getMockJobsList();
      console.log(
        `📊 Mock filter: Showing ${mockJobs.length} mock jobs for mock-contract`,
      );
      return mockJobs;
    }

    const queryParams = contractTypeId
      ? `?contractType=${encodeURIComponent(contractTypeId)}`
      : "";
    const { body: responseBody } = await get({
      apiName,
      path: `/jobs${queryParams}`,
    }).response;

    const jobs = (await responseBody.json()) as unknown as Job[];

    // Early return if mock disabled (performance optimization)
    if (import.meta.env.VITE_ENABLE_MOCK_JOBS !== "true") {
      return jobs;
    }

    // Only add mock data when no specific filter or real contract type filter
    const mockJobs = getMockJobsList();
    console.log(
      `📊 Mock enabled: Adding ${mockJobs.length} mock jobs to ${jobs.length} real jobs`,
    );
    return [...jobs, ...mockJobs];
  } catch (e: unknown) {
    console.error("GET call failed: ", getErrorMessage(e));
    throw e;
  }
}

export async function getJob(jobId: string) {
  console.log("Getting job:", jobId);

  // Early return if mock disabled (performance optimization)
  if (import.meta.env.VITE_ENABLE_MOCK_JOBS === "true" && isMockJobId(jobId)) {
    const mockJob = getMockJobById(jobId);
    if (mockJob) return mockJob;
  }

  try {
    const { body: responseBody } = await get({
      apiName,
      path: `/jobs/${jobId}`,
    }).response;

    return (await responseBody.json()) as unknown as Job;
  } catch (e: unknown) {
    console.error("GET call failed: ", getErrorMessage(e));
    throw e;
  }
}

export async function createJob(params: {
  documentS3Key: string;
  jobDescription: string;
  contractTypeId: string;
  outputLanguage: string;
  legislationId?: string;
}) {
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();

    const requestBody: {
      documentS3Key: string;
      jobDescription: string;
      contractTypeId: string;
      outputLanguage: string;
      additionalChecks?: {
        legislationCheck: {
          legislationId: string;
        };
      };
    } = {
      documentS3Key: params.documentS3Key,
      jobDescription: params.jobDescription,
      contractTypeId: params.contractTypeId,
      outputLanguage: params.outputLanguage,
    };

    // Only add additionalChecks.legislationCheck if legislationId is provided
    if (params.legislationId) {
      requestBody.additionalChecks = {
        legislationCheck: {
          legislationId: params.legislationId,
        },
      };
    }

    const restOperation = post({
      apiName: env.VITE_API_NAME,
      path: `/jobs`,
      options: {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: requestBody,
      },
    });
    const response = await restOperation.response;
    return response.body.json();
  } catch (e: unknown) {
    console.log("POST call failed: ", getErrorMessage(e));
    throw e;
  }
}

export async function getContractTypes() {
  console.log("Getting contract types");
  try {
    const { body: responseBody } = await get({
      apiName,
      path: "/contract-types",
    }).response;

    const contractTypes =
      (await responseBody.json()) as unknown as ContractType[];

    return contractTypes;
  } catch (e: unknown) {
    console.error("GET contract types failed: ", getErrorMessage(e));
    throw e;
  }
}

export async function getContractType(contractTypeId: string) {
  console.log("Getting contract type:", contractTypeId);
  try {
    const { body: responseBody } = await get({
      apiName,
      path: `/contract-types/${contractTypeId}`,
    }).response;

    return (await responseBody.json()) as unknown as Promise<ContractType>;
  } catch (e: unknown) {
    console.error("GET contract type failed: ", getErrorMessage(e));
    throw e;
  }
}

export async function createContractType(contractTypeData: {
  name: string;
  description: string;
  companyPartyType: string;
  otherPartyType: string;
  highRiskThreshold: number;
  mediumRiskThreshold: number;
  lowRiskThreshold: number;
  defaultLanguage: string;
  isActive: boolean;
}) {
  console.log("Creating contract type:", contractTypeData.name);
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();

    const restOperation = post({
      apiName,
      path: "/contract-types",
      options: {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: contractTypeData,
      },
    });

    const response = await restOperation.response;
    return (await response.body.json()) as unknown as Promise<ContractType>;
  } catch (e: unknown) {
    console.error("POST contract type failed: ", getErrorMessage(e));
    throw e;
  }
}

export async function updateContractType(
  contractTypeId: string,
  contractTypeData: Partial<{
    name: string;
    description: string;
    companyPartyType: string;
    otherPartyType: string;
    highRiskThreshold: number;
    mediumRiskThreshold: number;
    lowRiskThreshold: number;
    defaultLanguage: string;
    isActive: boolean;
  }>,
) {
  console.log("Updating contract type:", contractTypeId);
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();

    const restOperation = put({
      apiName,
      path: `/contract-types/${contractTypeId}`,
      options: {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: contractTypeData,
      },
    });

    const response = await restOperation.response;
    return (await response.body.json()) as unknown as Promise<ContractType>;
  } catch (e: unknown) {
    console.error("PUT contract type failed: ", getErrorMessage(e));
    throw e;
  }
}

export async function deleteContractType(contractTypeId: string) {
  console.log("Deleting contract type:", contractTypeId);
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();

    const restOperation = del({
      apiName,
      path: `/contract-types/${contractTypeId}`,
      options: {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      },
    });

    const response = await restOperation.response;

    // DELETE operations typically return 204 No Content with empty body
    // Don't try to parse JSON from empty response
    if (response.statusCode === 204) {
      return { success: true };
    }

    // For other status codes, try to parse JSON response
    return response.body.json();
  } catch (e: unknown) {
    console.error("DELETE contract type failed: ", getErrorMessage(e));
    throw e;
  }
}

// Guidelines API functions
export async function getGuidelines(
  contractTypeId: string,
  options?: {
    search?: string;
    level?: string;
    limit?: number;
    lastEvaluatedKey?: string;
  },
): Promise<GuidelinesListResponse> {
  console.log("Getting guidelines for contract type:", contractTypeId);
  try {
    const params = new URLSearchParams();
    params.append("contract_type_id", contractTypeId);
    if (options?.search) params.append("search", options.search);
    if (options?.level) params.append("level", options.level);
    if (options?.limit) params.append("limit", options.limit.toString());
    if (options?.lastEvaluatedKey)
      params.append("last_evaluated_key", options.lastEvaluatedKey);

    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();

    const restOperation = get({
      apiName,
      path: `/guidelines?${params.toString()}`,
      options: { headers: token ? { Authorization: `Bearer ${token}` } : {} },
    });

    const response = await restOperation.response;
    return (await response.body.json()) as unknown as GuidelinesListResponse;
  } catch (e: unknown) {
    console.error("GET guidelines failed: ", getErrorMessage(e));
    throw e;
  }
}

export async function getGuideline(
  contractTypeId: string,
  clauseTypeId: string,
): Promise<Guideline> {
  console.log("Getting guideline:", contractTypeId, clauseTypeId);
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();

    const restOperation = get({
      apiName,
      path: `/guidelines/${contractTypeId}/${clauseTypeId}`,
      options: { headers: token ? { Authorization: `Bearer ${token}` } : {} },
    });

    const response = await restOperation.response;
    return (await response.body.json()) as unknown as Guideline;
  } catch (e: unknown) {
    console.error("GET guideline failed: ", getErrorMessage(e));
    throw e;
  }
}

export async function createGuideline(
  contractTypeId: string,
  guidelineData: GuidelineFormData,
): Promise<Guideline> {
  console.log("Creating guideline:", guidelineData.name);
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();

    const requestBody = {
      contractTypeId,
      // clauseTypeId is now auto-generated by the backend
      name: guidelineData.name,
      standardWording: guidelineData.standardWording,
      level: guidelineData.level,
      evaluationQuestions: guidelineData.evaluationQuestions,
      examples: guidelineData.examples,
    };

    const restOperation = post({
      apiName,
      path: "/guidelines",
      options: {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: requestBody,
      },
    });

    const response = await restOperation.response;
    return (await response.body.json()) as unknown as Guideline;
  } catch (e: unknown) {
    console.error("POST guideline failed: ", getErrorMessage(e));
    throw e;
  }
}

export async function updateGuideline(
  contractTypeId: string,
  clauseTypeId: string,
  updates: Partial<Omit<GuidelineFormData, "clauseTypeId">>,
): Promise<Guideline> {
  console.log("Updating guideline:", contractTypeId, clauseTypeId);
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();

    const restOperation = put({
      apiName,
      path: `/guidelines/${contractTypeId}/${clauseTypeId}`,
      options: {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: updates,
      },
    });

    const response = await restOperation.response;
    return (await response.body.json()) as unknown as Guideline;
  } catch (e: unknown) {
    console.error("PUT guideline failed: ", getErrorMessage(e));
    throw e;
  }
}

export async function deleteGuideline(
  contractTypeId: string,
  clauseTypeId: string,
): Promise<void> {
  console.log("Deleting guideline:", contractTypeId, clauseTypeId);
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();

    const restOperation = del({
      apiName,
      path: `/guidelines/${contractTypeId}/${clauseTypeId}`,
      options: { headers: token ? { Authorization: `Bearer ${token}` } : {} },
    });

    await restOperation.response;
  } catch (e: unknown) {
    console.error("DELETE guideline failed: ", getErrorMessage(e));
    throw e;
  }
}

// Legislation API functions
interface LegislationApiResponse {
  id: string;
  subject_matter: string;
  name: string;
  s3_key?: string;
  s3Key?: string;
}

export async function getLegislations(): Promise<Legislation[]> {
  console.log("Getting legislations");
  try {
    const { body: responseBody } = await get({
      apiName,
      path: "/legislations",
    }).response;

    const rawData =
      (await responseBody.json()) as unknown as LegislationApiResponse[];

    // Map the backend response to our frontend interface
    // Backend uses snake_case, frontend uses camelCase
    return rawData.map((item: LegislationApiResponse) => ({
      id: item.id,
      subjectMatter: item.subject_matter,
      name: item.name,
      s3Key: item.s3_key || item.s3Key,
    }));
  } catch (e: unknown) {
    console.error("GET legislations failed: ", getErrorMessage(e));
    throw e;
  }
}

// Import API functions
export async function createImportJob(params: {
  documentS3Key: string;
  description?: string;
}): Promise<{ importJobId: string; contractTypeId: string; status: string }> {
  console.log("Creating import job for document:", params.documentS3Key);
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();

    const restOperation = post({
      apiName,
      path: "/import/contract-types",
      options: {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: params,
      },
    });

    const response = await restOperation.response;
    return (await response.body.json()) as unknown as Promise<{
      importJobId: string;
      contractTypeId: string;
      status: string;
    }>;
  } catch (e: unknown) {
    console.error("POST import job failed: ", getErrorMessage(e));
    throw e;
  }
}

export async function getImportJobStatus(importJobId: string): Promise<{
  status: "processing" | "completed" | "failed";
  progress: number;
  contractTypeId?: string;
  error?: string;
}> {
  console.log("Getting import job status:", importJobId);
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();

    const restOperation = get({
      apiName,
      path: `/import/contract-types/${importJobId}`,
      options: { headers: token ? { Authorization: `Bearer ${token}` } : {} },
    });

    const response = await restOperation.response;
    const data = (await response.body.json()) as {
      status: string;
      progress?: number;
      contractTypeId?: string;
      errorMessage?: string;
    };

    // Map backend status values to frontend expected values
    let mappedStatus: "processing" | "completed" | "failed";
    switch (data.status) {
      case "SUCCEEDED":
        mappedStatus = "completed";
        break;
      case "FAILED":
      case "TIMED_OUT":
      case "ABORTED":
        mappedStatus = "failed";
        break;
      case "RUNNING":
      default:
        mappedStatus = "processing";
        break;
    }

    return {
      status: mappedStatus,
      progress: data.progress || 0,
      contractTypeId: data.contractTypeId,
      error: data.errorMessage,
    };
  } catch (e: unknown) {
    console.error("GET import job status failed: ", getErrorMessage(e));
    throw e;
  }
}

// AI Generation API functions
export async function generateEvaluationQuestions(
  contractTypeId: string,
  clauseTypeId: string,
  standardWording: string,
): Promise<{ questions: string[] }> {
  console.log(
    "Generating evaluation questions for guideline:",
    contractTypeId,
    clauseTypeId,
  );
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();

    const restOperation = post({
      apiName,
      path: `/guidelines/${contractTypeId}/${clauseTypeId}/generate-questions`,
      options: {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: { standardWording },
      },
    });

    const response = await restOperation.response;
    return (await response.body.json()) as unknown as { questions: string[] };
  } catch (e: unknown) {
    console.error("POST generate questions failed: ", getErrorMessage(e));
    throw e;
  }
}

export async function generateClauseExamples(
  contractTypeId: string,
  clauseTypeId: string,
  standardWording: string,
): Promise<{ examples: string[] }> {
  console.log(
    "Generating clause examples for guideline:",
    contractTypeId,
    clauseTypeId,
  );
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();

    const restOperation = post({
      apiName,
      path: `/guidelines/${contractTypeId}/${clauseTypeId}/generate-examples`,
      options: {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: { standardWording },
      },
    });

    const response = await restOperation.response;
    return (await response.body.json()) as unknown as { examples: string[] };
  } catch (e: unknown) {
    console.error("POST generate examples failed: ", getErrorMessage(e));
    throw e;
  }
}
