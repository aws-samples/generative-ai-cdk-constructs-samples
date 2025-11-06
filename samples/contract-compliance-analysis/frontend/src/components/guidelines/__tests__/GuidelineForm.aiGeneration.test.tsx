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

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { GuidelineForm } from '../GuidelineForm';
import * as api from '@/lib/api';
import type { ContractType } from '@/lib/types';

// Mock the API functions
vi.mock('@/lib/api', () => ({
  generateEvaluationQuestions: vi.fn(),
  generateClauseExamples: vi.fn(),
}));

// Mock the translation hook
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) => {
      const translations: Record<string, string> = {
        'guidelines.form.fields.name.label': 'Name',
        'guidelines.form.fields.name.placeholder': 'Enter name...',
        'guidelines.form.fields.standardWording.label': 'Standard Wording',
        'guidelines.form.fields.standardWording.placeholder': 'Enter standard wording...',
        'guidelines.form.fields.standardWording.characterCount': '{{count}}/2000 characters',
        'guidelines.form.fields.impactLevel.label': 'Impact Level',
        'guidelines.form.fields.evaluationQuestions.label': 'Evaluation Questions',
        'guidelines.form.fields.evaluationQuestions.maxLabel': '(Max 10)',
        'guidelines.form.fields.evaluationQuestions.placeholder': 'Enter an evaluation question...',
        'guidelines.form.fields.evaluationQuestions.addPlaceholder': 'Add another evaluation question...',
        'guidelines.form.fields.evaluationQuestions.description': 'Questions used to evaluate compliance',
        'guidelines.form.fields.examples.label': 'Examples',
        'guidelines.form.fields.examples.optionalLabel': '(Optional, Max 20)',
        'guidelines.form.fields.examples.placeholder': 'Enter an example...',
        'guidelines.form.fields.examples.addPlaceholder': 'Add an example...',
        'guidelines.form.fields.examples.description': 'Example clauses or wording',
        'guidelines.form.actions.cancel': 'Cancel',
        'guidelines.form.actions.create': 'Create Guideline',
        'guidelines.form.actions.update': 'Update Guideline',
        'guidelines.form.aiGeneration.generateQuestions.button': 'Generate Questions',
        'guidelines.form.aiGeneration.generateQuestions.generating': 'Generating...',
        'guidelines.form.aiGeneration.generateQuestions.tooltip': 'Use AI to generate evaluation questions',
        'guidelines.form.aiGeneration.generateExamples.button': 'Generate Examples',
        'guidelines.form.aiGeneration.generateExamples.generating': 'Generating...',
        'guidelines.form.aiGeneration.generateExamples.tooltip': 'Use AI to generate alternative examples',
        'guidelines.form.aiGeneration.errors.requiresStandardWording': 'Please enter standard wording before generating content.',
        'guidelines.form.aiGeneration.errors.requiresContractType': 'Contract type information is required for generation.',
        'guidelines.form.aiGeneration.errors.generateQuestions': 'Failed to generate evaluation questions. Please try again.',
        'guidelines.form.aiGeneration.errors.generateExamples': 'Failed to generate examples. Please try again.',
        'job.compliance.impactLevel.high': 'High',
        'job.compliance.impactLevel.medium': 'Medium',
        'job.compliance.impactLevel.low': 'Low',
      };
      return options ? translations[key]?.replace(/\{\{(\w+)\}\}/g, (match: string, key: string) => options[key] || match) : translations[key] || key;
    },
  }),
}));

// Mock the validation utility
vi.mock('@/lib/validation', () => ({
  GuidelineValidator: {
    validateForm: vi.fn(() => ({ isValid: true, errors: {} })),
  },
}));

// Mock the form reset hook
vi.mock('@/hooks/useFormReset', () => ({
  useFormReset: () => ({
    markAsChanged: vi.fn(),
    handleCancel: vi.fn(() => true),
  }),
}));

// Mock the constants
vi.mock('@/lib/constants', () => ({
  IMPACT_COLORS: {
    high: 'text-red-600',
    medium: 'text-yellow-600',
    low: 'text-green-600',
  },
}));

describe('GuidelineForm AI Generation', () => {
  const mockOnSubmit = vi.fn();
  const mockOnCancel = vi.fn();
  const mockOnClearError = vi.fn();

  const mockContractType: ContractType = {
    contractTypeId: 'test-contract-type',
    name: 'Test Contract Type',
    description: 'Test Description',
    companyPartyType: 'Customer',
    otherPartyType: 'Service Provider',
    highRiskThreshold: 0,
    mediumRiskThreshold: 1,
    lowRiskThreshold: 3,
    isActive: true,
    defaultLanguage: 'en',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  };

  const defaultProps = {
    contractTypeId: 'test-contract-type',
    contractType: mockContractType,
    onSubmit: mockOnSubmit,
    onCancel: mockOnCancel,
    loading: false,
    error: null,
    onClearError: mockOnClearError,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders generate questions button', () => {
    render(<GuidelineForm {...defaultProps} />);

    expect(screen.getByRole('button', { name: 'Generate Questions' })).toBeInTheDocument();
  });

  it('renders generate examples button', () => {
    render(<GuidelineForm {...defaultProps} />);

    expect(screen.getByRole('button', { name: 'Generate Examples' })).toBeInTheDocument();
  });

  it('disables generate buttons when standard wording is empty', () => {
    render(<GuidelineForm {...defaultProps} />);

    const generateQuestionsBtn = screen.getByRole('button', { name: 'Generate Questions' });
    const generateExamplesBtn = screen.getByRole('button', { name: 'Generate Examples' });

    expect(generateQuestionsBtn).toBeDisabled();
    expect(generateExamplesBtn).toBeDisabled();
  });

  it('enables generate buttons when standard wording is provided', () => {
    render(<GuidelineForm {...defaultProps} />);

    // Fill in standard wording
    const standardWordingInput = screen.getByPlaceholderText('Enter standard wording...');
    fireEvent.change(standardWordingInput, { target: { value: 'Test standard wording' } });

    const generateQuestionsBtn = screen.getByRole('button', { name: 'Generate Questions' });
    const generateExamplesBtn = screen.getByRole('button', { name: 'Generate Examples' });

    expect(generateQuestionsBtn).not.toBeDisabled();
    expect(generateExamplesBtn).not.toBeDisabled();
  });

  it('disables generate buttons when contract type is missing', () => {
    const propsWithoutContractType = {
      ...defaultProps,
      contractType: undefined,
    };

    render(<GuidelineForm {...propsWithoutContractType} />);

    // Fill in standard wording
    const standardWordingInput = screen.getByPlaceholderText('Enter standard wording...');
    fireEvent.change(standardWordingInput, { target: { value: 'Test standard wording' } });

    const generateQuestionsBtn = screen.getByRole('button', { name: 'Generate Questions' });
    const generateExamplesBtn = screen.getByRole('button', { name: 'Generate Examples' });

    expect(generateQuestionsBtn).toBeDisabled();
    expect(generateExamplesBtn).toBeDisabled();
  });

  it('shows error when trying to generate without standard wording', async () => {
    render(<GuidelineForm {...defaultProps} />);

    // The button should be disabled when no standard wording is provided
    const generateQuestionsBtn = screen.getByRole('button', { name: 'Generate Questions' });
    expect(generateQuestionsBtn).toBeDisabled();
  });

  it('shows error when trying to generate without contract type', async () => {
    const propsWithoutContractType = {
      ...defaultProps,
      contractType: undefined,
    };

    render(<GuidelineForm {...propsWithoutContractType} />);

    // Fill in standard wording
    const standardWordingInput = screen.getByPlaceholderText('Enter standard wording...');
    fireEvent.change(standardWordingInput, { target: { value: 'Test standard wording' } });

    const generateQuestionsBtn = screen.getByRole('button', { name: 'Generate Questions' });
    // Button should be disabled when contract type is missing
    expect(generateQuestionsBtn).toBeDisabled();
  });

  it('calls generateEvaluationQuestions API when generate questions is clicked', async () => {
    const mockGenerateQuestions = vi.mocked(api.generateEvaluationQuestions);
    mockGenerateQuestions.mockResolvedValue({ questions: ['Generated question 1?', 'Generated question 2?'] });

    render(<GuidelineForm {...defaultProps} />);

    // Fill in standard wording
    const standardWordingInput = screen.getByPlaceholderText('Enter standard wording...');
    fireEvent.change(standardWordingInput, { target: { value: 'Test standard wording' } });

    // Click generate questions
    const generateQuestionsBtn = screen.getByRole('button', { name: 'Generate Questions' });
    fireEvent.click(generateQuestionsBtn);

    await waitFor(() => {
      expect(mockGenerateQuestions).toHaveBeenCalledWith(
        'test-contract-type',
        'temp', // temporary clauseTypeId for new guidelines
        'Test standard wording'
      );
    });
  });

  it('calls generateClauseExamples API when generate examples is clicked', async () => {
    const mockGenerateExamples = vi.mocked(api.generateClauseExamples);
    mockGenerateExamples.mockResolvedValue({ examples: ['Generated example 1', 'Generated example 2'] });

    render(<GuidelineForm {...defaultProps} />);

    // Fill in standard wording
    const standardWordingInput = screen.getByPlaceholderText('Enter standard wording...');
    fireEvent.change(standardWordingInput, { target: { value: 'Test standard wording' } });

    // Click generate examples
    const generateExamplesBtn = screen.getByRole('button', { name: 'Generate Examples' });
    fireEvent.click(generateExamplesBtn);

    await waitFor(() => {
      expect(mockGenerateExamples).toHaveBeenCalledWith(
        'test-contract-type',
        'temp', // temporary clauseTypeId for new guidelines
        'Test standard wording'
      );
    });
  });

  it('shows loading state when generating questions', async () => {
    const mockGenerateQuestions = vi.mocked(api.generateEvaluationQuestions);
    mockGenerateQuestions.mockImplementation(() => new Promise(resolve => setTimeout(() => resolve({ questions: [] }), 100)));

    render(<GuidelineForm {...defaultProps} />);

    // Fill in standard wording
    const standardWordingInput = screen.getByPlaceholderText('Enter standard wording...');
    fireEvent.change(standardWordingInput, { target: { value: 'Test standard wording' } });

    // Click generate questions
    const generateQuestionsBtn = screen.getByRole('button', { name: 'Generate Questions' });
    fireEvent.click(generateQuestionsBtn);

    // Should show loading state
    await waitFor(() => {
      expect(screen.getByText('Generating...')).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText('Generate Questions')).toBeInTheDocument();
    });
  });

  it('shows loading state when generating examples', async () => {
    const mockGenerateExamples = vi.mocked(api.generateClauseExamples);
    mockGenerateExamples.mockImplementation(() => new Promise(resolve => setTimeout(() => resolve({ examples: [] }), 100)));

    render(<GuidelineForm {...defaultProps} />);

    // Fill in standard wording
    const standardWordingInput = screen.getByPlaceholderText('Enter standard wording...');
    fireEvent.change(standardWordingInput, { target: { value: 'Test standard wording' } });

    // Click generate examples
    const generateExamplesBtn = screen.getByRole('button', { name: 'Generate Examples' });
    fireEvent.click(generateExamplesBtn);

    // Should show loading state
    await waitFor(() => {
      expect(screen.getByText('Generating...')).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText('Generate Examples')).toBeInTheDocument();
    });
  });

  it('handles API error when generating questions', async () => {
    const mockGenerateQuestions = vi.mocked(api.generateEvaluationQuestions);
    mockGenerateQuestions.mockRejectedValue(new Error('API Error'));

    render(<GuidelineForm {...defaultProps} />);

    // Fill in standard wording
    const standardWordingInput = screen.getByPlaceholderText('Enter standard wording...');
    fireEvent.change(standardWordingInput, { target: { value: 'Test standard wording' } });

    // Click generate questions
    const generateQuestionsBtn = screen.getByRole('button', { name: 'Generate Questions' });
    fireEvent.click(generateQuestionsBtn);

    await waitFor(() => {
      expect(screen.getByText('Failed to generate evaluation questions. Please try again.')).toBeInTheDocument();
    });
  });

  it('handles API error when generating examples', async () => {
    const mockGenerateExamples = vi.mocked(api.generateClauseExamples);
    mockGenerateExamples.mockRejectedValue(new Error('API Error'));

    render(<GuidelineForm {...defaultProps} />);

    // Fill in standard wording
    const standardWordingInput = screen.getByPlaceholderText('Enter standard wording...');
    fireEvent.change(standardWordingInput, { target: { value: 'Test standard wording' } });

    // Click generate examples
    const generateExamplesBtn = screen.getByRole('button', { name: 'Generate Examples' });
    fireEvent.click(generateExamplesBtn);

    await waitFor(() => {
      expect(screen.getByText('Failed to generate examples. Please try again.')).toBeInTheDocument();
    });
  });

  it('uses existing clauseTypeId for editing guidelines', async () => {
    const mockGenerateQuestions = vi.mocked(api.generateEvaluationQuestions);
    mockGenerateQuestions.mockResolvedValue({ questions: ['Generated question?'] });

    const existingGuideline = {
      contractTypeId: 'test-contract-type',
      clauseTypeId: 'existing-clause-type',
      name: 'Existing Guideline',
      standardWording: 'Existing standard wording',
      level: 'medium' as const,
      evaluationQuestions: ['Existing question?'],
      examples: ['Existing example'],
    };

    const propsWithGuideline = {
      ...defaultProps,
      guideline: existingGuideline,
    };

    render(<GuidelineForm {...propsWithGuideline} />);

    // Click generate questions
    const generateQuestionsBtn = screen.getByRole('button', { name: 'Generate Questions' });
    fireEvent.click(generateQuestionsBtn);

    await waitFor(() => {
      expect(mockGenerateQuestions).toHaveBeenCalledWith(
        'test-contract-type',
        'existing-clause-type', // should use existing clauseTypeId
        'Existing standard wording'
      );
    });
  });
});