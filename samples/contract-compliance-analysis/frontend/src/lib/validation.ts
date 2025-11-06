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

import type { GuidelineFormData } from '@lib/types';

export interface ValidationError {
  field: string;
  message: string;
}

export interface FormValidationResult {
  isValid: boolean;
  errors: Record<string, string>;
}

export class GuidelineValidator {
  // Removed validateClauseTypeId since it's now auto-generated

  static validateName(name: string): string | null {
    if (!name.trim()) {
      return 'Name is required';
    }

    if (name.length > 100) {
      return 'Name must be 100 characters or less';
    }

    return null;
  }

  static validateStandardWording(standardWording: string): string | null {
    if (!standardWording.trim()) {
      return 'Standard wording is required';
    }

    if (standardWording.length > 2000) {
      return 'Standard wording must be 2000 characters or less';
    }

    return null;
  }

  static validateEvaluationQuestions(questions: string[]): string | null {
    const validQuestions = questions.filter(q => q.trim());

    if (validQuestions.length === 0) {
      return 'At least one evaluation question is required';
    }

    if (validQuestions.length > 10) {
      return 'Maximum 10 evaluation questions allowed';
    }

    if (validQuestions.some(q => q.length > 500)) {
      return 'Evaluation questions must be 500 characters or less';
    }

    return null;
  }

  static validateExamples(examples: string[]): string | null {
    const validExamples = examples.filter(e => e.trim());

    if (validExamples.length > 20) {
      return 'Maximum 20 examples allowed';
    }

    if (validExamples.some(e => e.length > 1000)) {
      return 'Examples must be 1000 characters or less';
    }

    return null;
  }

  static validateForm(data: GuidelineFormData): FormValidationResult {
    const errors: Record<string, string> = {};

    // Clause type ID is now auto-generated, so no validation needed

    // Validate name
    const nameError = this.validateName(data.name);
    if (nameError) {
      errors.name = nameError;
    }

    // Validate standard wording
    const standardWordingError = this.validateStandardWording(data.standardWording);
    if (standardWordingError) {
      errors.standardWording = standardWordingError;
    }

    // Validate evaluation questions
    const questionsError = this.validateEvaluationQuestions(data.evaluationQuestions);
    if (questionsError) {
      errors.evaluationQuestions = questionsError;
    }

    // Validate examples
    const examplesError = this.validateExamples(data.examples);
    if (examplesError) {
      errors.examples = examplesError;
    }

    return {
      isValid: Object.keys(errors).length === 0,
      errors,
    };
  }
}

export function parseServerError(error: unknown): string {
  if (typeof error === 'string') {
    return error;
  }

  if (error && typeof error === 'object') {
    // Handle AWS API Gateway error format
    if ('response' in error && error.response && typeof error.response === 'object') {
      const response = error.response as Record<string, unknown>;

      if (response.body && typeof response.body === 'object') {
        const body = response.body as Record<string, unknown>;
        if (body.message && typeof body.message === 'string') {
          return body.message;
        }
        if (body.error && typeof body.error === 'string') {
          return body.error;
        }
      }

      if (response.status) {
        switch (response.status) {
          case 400:
            return 'Invalid request. Please check your input and try again.';
          case 401:
            return 'You are not authorized to perform this action. Please log in and try again.';
          case 403:
            return 'You do not have permission to perform this action.';
          case 404:
            return 'The requested guideline was not found.';
          case 409:
            return 'A guideline with this clause type ID already exists.';
          case 500:
            return 'An internal server error occurred. Please try again later.';
          default:
            return `Request failed with status ${response.status}`;
        }
      }
    }

    // Handle standard Error objects
    if ('message' in error && typeof error.message === 'string') {
      return error.message;
    }

    // Handle validation errors
    if ('errors' in error && Array.isArray(error.errors)) {
      return error.errors.map((e: unknown) => {
        if (typeof e === 'string') return e;
        if (e && typeof e === 'object' && 'message' in e && typeof e.message === 'string') {
          return e.message;
        }
        return String(e);
      }).join(', ');
    }
  }

  return 'An unexpected error occurred. Please try again.';
}

export function getFieldErrorMessage(error: unknown, field: string): string | null {
  if (error && typeof error === 'object' && 'response' in error) {
    const response = error.response as Record<string, unknown>;

    if (response?.body && typeof response.body === 'object') {
      const body = response.body as Record<string, unknown>;

      if (body.errors && Array.isArray(body.errors)) {
        const fieldError = body.errors.find((e: unknown) => {
          return e && typeof e === 'object' && 'field' in e && e.field === field;
        });
        if (fieldError && typeof fieldError === 'object' && 'message' in fieldError && typeof fieldError.message === 'string') {
          return fieldError.message;
        }
      }

      if (body.fieldErrors && typeof body.fieldErrors === 'object') {
        const fieldErrors = body.fieldErrors as Record<string, unknown>;
        const errorMessage = fieldErrors[field];
        return typeof errorMessage === 'string' ? errorMessage : null;
      }
    }
  }

  return null;
}