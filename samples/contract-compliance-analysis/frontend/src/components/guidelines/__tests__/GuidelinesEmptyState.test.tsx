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
import { render, screen, fireEvent } from '@testing-library/react';
import { GuidelinesEmptyState } from '../GuidelinesEmptyState';
import type { ContractType } from '../../../lib/types';

// Mock react-i18next
vi.mock('react-i18next', async (importOriginal) => {
  const actual = await importOriginal() as Record<string, unknown>;
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string) => {
        const translations: Record<string, string> = {
          'guidelines.noGuidelines.title': 'No Guidelines Found',
          'guidelines.noGuidelines.description': 'No guidelines have been created for this contract type yet. Click "Create Guideline" to add your first compliance guideline.',
          'guidelines.createNew': 'Create Guideline',
        };
        return translations[key] || key;
      },
    }),
  };
});

const mockContractType: ContractType = {
  contractTypeId: 'service-agreement',
  name: 'Service Agreement',
  description: 'Standard service agreement contract',
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

describe('GuidelinesEmptyState', () => {
  const mockOnCreateGuideline = vi.fn();
  const mockOnImportFromDocument = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders basic empty state', () => {
    render(<GuidelinesEmptyState />);

    expect(screen.getByText('No Guidelines Found')).toBeInTheDocument();
    expect(screen.getByText(/No guidelines have been created for this contract type yet/)).toBeInTheDocument();
  });

  it('renders with contract type specific message', () => {
    render(
      <GuidelinesEmptyState
        contractType={mockContractType}
      />
    );

    expect(screen.getByText('No Guidelines Found')).toBeInTheDocument();
    expect(screen.getByText(/No guidelines have been created for "Service Agreement" yet/)).toBeInTheDocument();
  });

  it('shows create guideline button when handler is provided', () => {
    render(
      <GuidelinesEmptyState
        onCreateGuideline={mockOnCreateGuideline}
      />
    );

    const createButton = screen.getByText('Create Guideline');
    expect(createButton).toBeInTheDocument();

    fireEvent.click(createButton);
    expect(mockOnCreateGuideline).toHaveBeenCalledTimes(1);
  });

  it('shows import button when import option is enabled', () => {
    render(
      <GuidelinesEmptyState
        onImportFromDocument={mockOnImportFromDocument}
        showImportOption={true}
      />
    );

    const importButton = screen.getByText('Import from Document');
    expect(importButton).toBeInTheDocument();

    fireEvent.click(importButton);
    expect(mockOnImportFromDocument).toHaveBeenCalledTimes(1);
  });

  it('shows both buttons when both handlers are provided', () => {
    render(
      <GuidelinesEmptyState
        contractType={mockContractType}
        onCreateGuideline={mockOnCreateGuideline}
        onImportFromDocument={mockOnImportFromDocument}
        showImportOption={true}
      />
    );

    expect(screen.getByText('Create Guideline')).toBeInTheDocument();
    expect(screen.getByText('Import from Document')).toBeInTheDocument();
  });

  it('does not show import button when showImportOption is false', () => {
    render(
      <GuidelinesEmptyState
        onImportFromDocument={mockOnImportFromDocument}
        showImportOption={false}
      />
    );

    expect(screen.queryByText('Import from Document')).not.toBeInTheDocument();
  });

  it('does not show create button when handler is not provided', () => {
    render(<GuidelinesEmptyState />);

    expect(screen.queryByText('Create Guideline')).not.toBeInTheDocument();
  });

  it('renders book icon', () => {
    render(<GuidelinesEmptyState />);

    // Check for the presence of an SVG element (BookOpenIcon)
    const svgElement = document.querySelector('svg');
    expect(svgElement).toBeInTheDocument();
  });

  it('handles missing contract type gracefully', () => {
    render(
      <GuidelinesEmptyState
        contractType={undefined}
        onCreateGuideline={mockOnCreateGuideline}
      />
    );

    expect(screen.getByText('No Guidelines Found')).toBeInTheDocument();
    expect(screen.getByText('Create Guideline')).toBeInTheDocument();
  });
});