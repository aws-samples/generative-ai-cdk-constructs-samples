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
import { GenerationReviewDialog } from '../GenerationReviewDialog';

// Mock the translation hook
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) => {
      const translations: Record<string, string> = {
        'guidelines.form.aiGeneration.reviewDialog.title': 'Review Generated Content',
        'guidelines.form.aiGeneration.reviewDialog.description': 'Review the AI-generated content below.',
        'guidelines.form.aiGeneration.reviewDialog.questionsTitle': 'Generated Evaluation Questions',
        'guidelines.form.aiGeneration.reviewDialog.examplesTitle': 'Generated Examples',
        'guidelines.form.aiGeneration.reviewDialog.empty': 'No content was generated.',
        'guidelines.form.aiGeneration.reviewDialog.placeholder': 'Edit this item...',
        'guidelines.form.aiGeneration.reviewDialog.actions.apply': 'Apply to Guideline',
        'guidelines.form.aiGeneration.reviewDialog.actions.cancel': 'Cancel',
        'guidelines.form.aiGeneration.reviewDialog.actions.edit': 'Edit item',
        'guidelines.form.aiGeneration.reviewDialog.actions.remove': 'Remove item',
        'guidelines.form.fields.evaluationQuestions.addPlaceholder': 'Add another evaluation question...',
        'guidelines.form.fields.examples.addPlaceholder': 'Add an example...',
      };
      return options ? translations[key]?.replace(/\{\{(\w+)\}\}/g, (match: string, key: string) => options[key] || match) : translations[key] || key;
    },
  }),
}));

describe('GenerationReviewDialog', () => {
  const mockOnApply = vi.fn();
  const mockOnOpenChange = vi.fn();

  const defaultProps = {
    open: true,
    onOpenChange: mockOnOpenChange,
    type: 'questions' as const,
    generatedContent: ['Question 1?', 'Question 2?'],
    onApply: mockOnApply,
    loading: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders dialog with generated questions', () => {
    render(<GenerationReviewDialog {...defaultProps} />);

    expect(screen.getByText('Review Generated Content')).toBeInTheDocument();
    expect(screen.getByText('Generated Evaluation Questions')).toBeInTheDocument();
    expect(screen.getByText('Question 1?')).toBeInTheDocument();
    expect(screen.getByText('Question 2?')).toBeInTheDocument();
    expect(screen.getByText('2 / 10')).toBeInTheDocument(); // Badge showing count
  });

  it('renders dialog with generated examples', () => {
    const props = {
      ...defaultProps,
      type: 'examples' as const,
      generatedContent: ['Example 1', 'Example 2'],
    };

    render(<GenerationReviewDialog {...props} />);

    expect(screen.getByText('Generated Examples')).toBeInTheDocument();
    expect(screen.getByText('Example 1')).toBeInTheDocument();
    expect(screen.getByText('Example 2')).toBeInTheDocument();
    expect(screen.getByText('2 / 20')).toBeInTheDocument(); // Badge showing count for examples
  });

  it('shows empty state when no content is generated', () => {
    const props = {
      ...defaultProps,
      generatedContent: [],
    };

    render(<GenerationReviewDialog {...props} />);

    expect(screen.getByText('No content was generated.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Apply to Guideline' })).toBeDisabled();
  });

  it('allows editing an item', async () => {
    render(<GenerationReviewDialog {...defaultProps} />);

    // Click edit button for first item
    const editButtons = screen.getAllByLabelText('Edit item');
    fireEvent.click(editButtons[0]);

    // Should show input field
    const input = screen.getByDisplayValue('Question 1?');
    expect(input).toBeInTheDocument();

    // Edit the content
    fireEvent.change(input, { target: { value: 'Updated Question 1?' } });

    // Save the edit
    const saveButtons = screen.getAllByRole('button');
    const saveButton = saveButtons.find(btn => btn.querySelector('svg polyline')); // CheckIcon button
    expect(saveButton).toBeDefined();
    fireEvent.click(saveButton!);

    await waitFor(() => {
      expect(screen.getByText('Updated Question 1?')).toBeInTheDocument();
    });
  });

  it('allows removing an item', () => {
    render(<GenerationReviewDialog {...defaultProps} />);

    // Click remove button for first item
    const removeButtons = screen.getAllByLabelText('Remove item');
    fireEvent.click(removeButtons[0]);

    // First question should be removed
    expect(screen.queryByText('Question 1?')).not.toBeInTheDocument();
    expect(screen.getByText('Question 2?')).toBeInTheDocument();
    expect(screen.getByText('1 / 10')).toBeInTheDocument(); // Updated count
  });

  it('allows adding a new item', () => {
    render(<GenerationReviewDialog {...defaultProps} />);

    // Find the add input field
    const addInput = screen.getByPlaceholderText('Add another evaluation question...');

    // Type new question
    fireEvent.change(addInput, { target: { value: 'New Question?' } });

    // Click add button
    const addButtons = screen.getAllByRole('button');
    const addButton = addButtons.find(btn => btn.querySelector('svg path[d*="M5 12h14"]')); // PlusIcon button
    expect(addButton).toBeDefined();
    fireEvent.click(addButton!);

    // New question should be added
    expect(screen.getByText('New Question?')).toBeInTheDocument();
    expect(screen.getByText('3 / 10')).toBeInTheDocument(); // Updated count
    expect(addInput).toHaveValue(''); // Input should be cleared
  });

  it('calls onApply with edited content when apply is clicked', () => {
    render(<GenerationReviewDialog {...defaultProps} />);

    // Click apply button
    const applyButton = screen.getByRole('button', { name: 'Apply to Guideline' });
    fireEvent.click(applyButton);

    expect(mockOnApply).toHaveBeenCalledWith(['Question 1?', 'Question 2?']);
  });

  it('calls onOpenChange when cancel is clicked', () => {
    render(<GenerationReviewDialog {...defaultProps} />);

    // Click cancel button
    const cancelButton = screen.getByRole('button', { name: 'Cancel' });
    fireEvent.click(cancelButton);

    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
  });

  it('handles keyboard shortcuts for editing', () => {
    render(<GenerationReviewDialog {...defaultProps} />);

    // Start editing first item
    const editButtons = screen.getAllByLabelText('Edit item');
    fireEvent.click(editButtons[0]);

    const input = screen.getByDisplayValue('Question 1?');

    // Test Enter key to save
    fireEvent.change(input, { target: { value: 'Updated via Enter' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(screen.getByText('Updated via Enter')).toBeInTheDocument();
  });

  it('handles keyboard shortcuts for canceling edit', () => {
    render(<GenerationReviewDialog {...defaultProps} />);

    // Start editing first item
    const editButtons = screen.getAllByLabelText('Edit item');
    fireEvent.click(editButtons[0]);

    const input = screen.getByDisplayValue('Question 1?');

    // Test Escape key to cancel
    fireEvent.change(input, { target: { value: 'This should be cancelled' } });
    fireEvent.keyDown(input, { key: 'Escape' });

    // Should revert to original content
    expect(screen.getByText('Question 1?')).toBeInTheDocument();
    expect(screen.queryByText('This should be cancelled')).not.toBeInTheDocument();
  });

  it('respects maximum item limits', () => {
    // Test with questions (max 10)
    const manyQuestions = Array.from({ length: 10 }, (_, i) => `Question ${i + 1}?`);
    const props = {
      ...defaultProps,
      generatedContent: manyQuestions,
    };

    render(<GenerationReviewDialog {...props} />);

    // Should not show add input when at max
    expect(screen.queryByPlaceholderText('Add another evaluation question...')).not.toBeInTheDocument();
    expect(screen.getByText('10 / 10')).toBeInTheDocument();
  });

  it('respects maximum item limits for examples', () => {
    // Test with examples (max 20)
    const manyExamples = Array.from({ length: 20 }, (_, i) => `Example ${i + 1}`);
    const props = {
      ...defaultProps,
      type: 'examples' as const,
      generatedContent: manyExamples,
    };

    render(<GenerationReviewDialog {...props} />);

    // Should not show add input when at max
    expect(screen.queryByPlaceholderText('Add an example...')).not.toBeInTheDocument();
    expect(screen.getByText('20 / 20')).toBeInTheDocument();
  });
});