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

/**
 * Utility functions for mock data management
 */

/**
 * Check if mock data should be used based on environment variable
 */
export function shouldUseMockData(): boolean {
  return import.meta.env.VITE_ENABLE_MOCK_JOBS === "true";
}

/**
 * Check if a job ID belongs to mock data
 */
export function isMockJobId(jobId: string): boolean {
  return jobId.startsWith("mock-job-");
}

/**
 * Inject mock data into real data if mock is enabled
 */
export function injectMockData<T>(realData: T[], mockData: T[]): T[] {
  if (!shouldUseMockData()) {
    return realData;
  }

  console.log(
    `📊 Mock enabled: Adding ${mockData.length} mock items to ${realData.length} real items`,
  );
  return [...realData, ...mockData];
}
