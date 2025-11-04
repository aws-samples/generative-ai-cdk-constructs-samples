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
import { ContractTypeSelect } from '../ContractTypeSelect';
import * as api from '../../lib/api';
import type { ContractType } from '../../lib/types';

// Mock the API
vi.mock('../../lib/api');
const mockGetContractTypes = vi.mocked(api.getContractTypes);

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'contractType.label': 'Contract Type',
        'contractType.placeholder': 'Select a contract type',
        'contractType.loadError': 'Failed to load contract types',
        'contractType.noTypesAvailable': 'No contract types are currently available',
      };
      return translations[key] || key;
    },
  }),
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
    isActive: true,
    defaultLanguage: 'en',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  {
    contractTypeId: 'inactive-type',
    name: 'Inactive Type',
    description: 'This type is inactive',
    companyPartyType: 'Company',
    otherPartyType: 'Other',
    highRiskThreshold: 0,
    mediumRiskThreshold: 1,
    lowRiskThreshold: 3,
    isActive: false,
    defaultLanguage: 'en',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
];

describe('ContractTypeSelect', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    mockGetContractTypes.mockImplementation(() => new Promise(() => {})); // Never resolves

    render(
      <ContractTypeSelect
        value=""
        onChange={mockOnChange}
      />
    );

    expect(screen.getByText('Contract Type')).toBeInTheDocument();
    // Should show loading skeleton
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('renders contract types after loading', async () => {
    mockGetContractTypes.mockResolvedValue(mockContractTypes);

    render(
      <ContractTypeSelect
        value=""
        onChange={mockOnChange}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Select a contract type')).toBeInTheDocument();
    });

    // Click to open dropdown
    fireEvent.click(screen.getByRole('combobox'));

    await waitFor(() => {
      expect(screen.getByText('Service Agreement')).toBeInTheDocument();
      expect(screen.getByText('Employment Contract')).toBeInTheDocument();
      // Inactive type should not be shown
      expect(screen.queryByText('Inactive Type')).not.toBeInTheDocument();
    });
  });

  it('auto-selects single active contract type', async () => {
    const singleActiveType = [mockContractTypes[0]]; // Only service agreement
    mockGetContractTypes.mockResolvedValue(singleActiveType);

    render(
      <ContractTypeSelect
        value=""
        onChange={mockOnChange}
      />
    );

    await waitFor(() => {
      expect(mockOnChange).toHaveBeenCalledWith('service-agreement');
    });
  });

  it('handles selection change', async () => {
    mockGetContractTypes.mockResolvedValue(mockContractTypes);

    render(
      <ContractTypeSelect
        value=""
        onChange={mockOnChange}
      />
    );

    // Wait for component to load
    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    // Open the select dropdown
    const trigger = screen.getByRole('combobox');
    fireEvent.click(trigger);

    // Wait for options to appear and select one
    await waitFor(() => {
      const option = screen.getByRole('option', { name: /Service Agreement/ });
      fireEvent.click(option);
    });

    expect(mockOnChange).toHaveBeenCalledWith('service-agreement');
  });

  it('displays error state when loading fails', async () => {
    const errorMessage = 'Network error';
    mockGetContractTypes.mockRejectedValue(new Error(errorMessage));

    render(
      <ContractTypeSelect
        value=""
        onChange={mockOnChange}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Failed to load contract types/)).toBeInTheDocument();
      expect(screen.getByText(/Network error/)).toBeInTheDocument();
    });
  });

  it('displays no types available message when empty', async () => {
    mockGetContractTypes.mockResolvedValue([]);

    render(
      <ContractTypeSelect
        value=""
        onChange={mockOnChange}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('No contract types are currently available')).toBeInTheDocument();
    });
  });

  it('shows required indicator when required prop is true', async () => {
    mockGetContractTypes.mockResolvedValue(mockContractTypes);

    render(
      <ContractTypeSelect
        value=""
        onChange={mockOnChange}
        required={true}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('*')).toBeInTheDocument();
    });
  });

  it('disables select when disabled prop is true', async () => {
    mockGetContractTypes.mockResolvedValue(mockContractTypes);

    render(
      <ContractTypeSelect
        value=""
        onChange={mockOnChange}
        disabled={true}
      />
    );

    await waitFor(() => {
      const combobox = screen.getByRole('combobox');
      expect(combobox).toBeDisabled();
    });
  });

  it('displays selected value correctly', async () => {
    mockGetContractTypes.mockResolvedValue(mockContractTypes);

    render(
      <ContractTypeSelect
        value="service-agreement"
        onChange={mockOnChange}
      />
    );

    await waitFor(() => {
      // Check that the selected value is displayed in the trigger
      expect(screen.getByText('Service Agreement')).toBeInTheDocument();
    });
  });
});