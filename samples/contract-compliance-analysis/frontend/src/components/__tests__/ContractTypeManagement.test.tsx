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
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router';
import { ContractTypeManagement } from '../ContractTypeManagement';
import * as api from '../../lib/api';
import type { ContractType } from '../../lib/types';

// Mock the API
vi.mock('../../lib/api');
const mockGetContractTypes = vi.mocked(api.getContractTypes);
const mockUpdateContractType = vi.mocked(api.updateContractType);

// Mock react-router
const mockNavigate = vi.fn();
vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock react-i18next
vi.mock('react-i18next', async (importOriginal) => {
  const actual = await importOriginal() as Record<string, unknown>;
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string) => {
        const translations: Record<string, string> = {
          'contractType.management.title': 'Contract Type Management',
          'contractType.management.description': 'Manage contract types and their settings',
          'contractType.management.createNew': 'Create New Type',
          'contractType.management.manageGuidelines': 'Manage Guidelines',
          'contractType.management.guidelinesColumn': 'Guidelines',
          'contractType.management.activate': 'Activate',
          'contractType.management.deactivate': 'Deactivate',
          'contractType.form.name': 'Name',
          'contractType.form.description': 'Description',
          'common.cancel': 'Cancel',
        };
        return translations[key] || key;
      },
    }),
  };
});

// Mock sonner
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const mockContractTypes: ContractType[] = [
  {
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
  },
  {
    contractTypeId: 'employment-contract',
    name: 'Employment Contract',
    description: 'Employee agreement contract',
    companyPartyType: 'Employer',
    otherPartyType: 'Employee',
    highRiskThreshold: 0,
    mediumRiskThreshold: 1,
    lowRiskThreshold: 3,
    isActive: false,
    defaultLanguage: 'en',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
];

// Wrapper component to provide router context
const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
);

describe('ContractTypeManagement', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    mockGetContractTypes.mockImplementation(() => new Promise(() => {})); // Never resolves

    render(
      <TestWrapper>
        <ContractTypeManagement />
      </TestWrapper>
    );

    expect(screen.getByText('Contract Type Management')).toBeInTheDocument();
    expect(screen.getByText('Manage contract types and their settings')).toBeInTheDocument();
    // Should show loading spinner
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders contract types table after loading', async () => {
    mockGetContractTypes.mockResolvedValue(mockContractTypes);

    render(
      <TestWrapper>
        <ContractTypeManagement />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Service Agreement')).toBeInTheDocument();
      expect(screen.getByText('Employment Contract')).toBeInTheDocument();
    });

    // Check table headers
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Description')).toBeInTheDocument();
    expect(screen.getByText('Guidelines')).toBeInTheDocument();

    // Check status badges
    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByText('Inactive')).toBeInTheDocument();
  });

  it('shows guidelines management button for each contract type', async () => {
    mockGetContractTypes.mockResolvedValue(mockContractTypes);

    render(
      <TestWrapper>
        <ContractTypeManagement />
      </TestWrapper>
    );

    await waitFor(() => {
      const guidelinesButtons = screen.getAllByText('Manage Guidelines');
      expect(guidelinesButtons).toHaveLength(2); // One for each contract type
    });
  });

  it('navigates to guidelines page when manage guidelines is clicked', async () => {
    mockGetContractTypes.mockResolvedValue(mockContractTypes);

    render(
      <TestWrapper>
        <ContractTypeManagement />
      </TestWrapper>
    );

    await waitFor(() => {
      const guidelinesButtons = screen.getAllByText('Manage Guidelines');
      fireEvent.click(guidelinesButtons[0]);
    });

    expect(mockNavigate).toHaveBeenCalledWith('/contract-types/service-agreement/guidelines');
  });

  it('opens create dialog when create button is clicked', async () => {
    mockGetContractTypes.mockResolvedValue(mockContractTypes);

    render(
      <TestWrapper>
        <ContractTypeManagement />
      </TestWrapper>
    );

    await waitFor(() => {
      const createButton = screen.getByText('Create New Type');
      fireEvent.click(createButton);
    });

    // Check that dialog is opened
    expect(screen.getByText('Create New Contract Type')).toBeInTheDocument();
  });

  it('shows action buttons for each contract type', async () => {
    mockGetContractTypes.mockResolvedValue(mockContractTypes);

    render(
      <TestWrapper>
        <ContractTypeManagement />
      </TestWrapper>
    );

    await waitFor(() => {
      // Check that action buttons are present
      const buttons = screen.getAllByRole('button');
      // Should have create button + 2 contract types * 4 buttons each (edit, manage guidelines, activate/deactivate, delete)
      expect(buttons.length).toBeGreaterThan(8);
    });
  });

  it('displays error state when loading fails', async () => {
    const errorMessage = 'Network error';
    mockGetContractTypes.mockRejectedValue(new Error(errorMessage));

    render(
      <TestWrapper>
        <ContractTypeManagement />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText(/Error loading contract types/)).toBeInTheDocument();
      expect(screen.getByText(/Network error/)).toBeInTheDocument();
    });
  });

  it('displays empty state when no contract types exist', async () => {
    mockGetContractTypes.mockResolvedValue([]);

    render(
      <TestWrapper>
        <ContractTypeManagement />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('No contract types found')).toBeInTheDocument();
    });
  });

  it('shows risk thresholds for each contract type', async () => {
    mockGetContractTypes.mockResolvedValue(mockContractTypes);

    render(
      <TestWrapper>
        <ContractTypeManagement />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getAllByText('High: 0')).toHaveLength(2);
      expect(screen.getAllByText('Med: 1')).toHaveLength(2);
      expect(screen.getAllByText('Low: 3')).toHaveLength(2);
    });
  });

  it('handles contract type activation/deactivation', async () => {
    mockGetContractTypes.mockResolvedValue(mockContractTypes);
    mockUpdateContractType.mockResolvedValue(mockContractTypes[1]);

    render(
      <TestWrapper>
        <ContractTypeManagement />
      </TestWrapper>
    );

    await waitFor(() => {
      const activateButton = screen.getByText('Activate');
      fireEvent.click(activateButton);
    });

    expect(mockUpdateContractType).toHaveBeenCalledWith('employment-contract', {
      name: 'Employment Contract',
      description: 'Employee agreement contract',
      companyPartyType: 'Employer',
      otherPartyType: 'Employee',
      highRiskThreshold: 0,
      mediumRiskThreshold: 1,
      lowRiskThreshold: 3,
      defaultLanguage: 'en',
      isActive: true
    });
  });
});