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

import { ApiError } from "aws-amplify/api";
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { Job, ChecksCollection } from "@/lib/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const getErrorMessage = (error: unknown): string => {
  let message: string;

  if (error instanceof ApiError) {
    if (error.response) {
      const { statusCode, body } = error.response;
      message = `Received ${statusCode} error response with payload: ${body}`;
    } else {
      message =
        "An error ocurred, but there was no response received from the server";
    }
  } else if (error instanceof Error) {
    message = error.message;
  } else if (error && typeof error === "object" && "message" in error) {
    message = String(error.message);
  } else if (typeof error === "string") {
    message = error;
  } else {
    message = "Unknown error";
  }

  return message;
};

export const removePrefix = (prefix: string, str: string) => {
  return str.startsWith(prefix) ? str.slice(prefix.length) : str;
};

/**
 * Determines if a job is overall compliant based on all checks.
 * Returns true if ALL checks are compliant (job is compliant overall).
 */
export function isOverallCompliant(job: Job): boolean {
  const { guidelines, legislation } = job.checks;

  if (!legislation) {
    return guidelines.compliant;
  }

  return guidelines.compliant && legislation.compliant;
}

/**
 * Gets the overall processing status based on checks.
 * If legislation check doesn't exist, only considers guidelines.
 * Priority: RUNNING > FAILED/TIMED_OUT/ABORTED > SUCCEEDED
 */
export function getOverallProcessingStatus(
  checks: ChecksCollection,
): "SUCCEEDED" | "FAILED" | "RUNNING" | "TIMED_OUT" | "ABORTED" {
  const { guidelines, legislation } = checks;

  // Se não tem legislation, considera apenas guidelines
  if (!legislation) {
    return guidelines.processingStatus;
  }

  // Se tem legislation, considera ambos
  // Prioridade: RUNNING > FAILED/TIMED_OUT/ABORTED > SUCCEEDED
  if (
    guidelines.processingStatus === "RUNNING" ||
    legislation.processingStatus === "RUNNING"
  ) {
    return "RUNNING";
  }

  // Se qualquer um falhou, retorna o status de falha
  if (guidelines.processingStatus !== "SUCCEEDED")
    return guidelines.processingStatus;
  if (legislation.processingStatus !== "SUCCEEDED")
    return legislation.processingStatus;

  // Ambos succeeded
  return "SUCCEEDED";
}

/**
 * Determines if a job is clickable (can navigate to detail page).
 * Job is clickable only when all applicable checks have SUCCEEDED.
 */
export function isJobClickable(checks: ChecksCollection): boolean {
  return getOverallProcessingStatus(checks) === "SUCCEEDED";
}
