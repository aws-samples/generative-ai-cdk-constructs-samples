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

export interface Job {
  job_id: string;
  filename: string;
  start_date?: string;
}

export interface Questionnaire {
  job_id: string;
  question_number: number;
  question: string;
  answer: string;
  topic: string;
  approved: boolean;
}

export type UploadState = {
  message?: string;
  loading?: boolean;
  complete?: boolean;
  error?: boolean;
  warning?: boolean;
};
