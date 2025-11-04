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
import { MemoryRouter } from 'react-router';
import { ContractTypeGuidelines } from '../ContractTypeGuidelines';
import * as api from '../../lib/api';
import type { ContractType, Guideline } from '../../lib/types';

// Mock the API
vi.mock('../../lib/api');
const mockGetContractType = vi.mocked(api.getContractType);

// Mock react-router
const mockNavigate = vi.fn();
const mockUseParams = vi.fn();
vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => mockUseParams(),
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
          'guidelines.title': 'Guidelines Management',
          'guidelines.description': 'Manage compliance guidelines for contract types',
          'guidelines.createNew': 'Create Guideline',
          'guidelines.noGuidelines.title': 'No Guidelines Found',
          'guidelines.noGuidelines.description': 'No guidelines have been created for this contract type yet.',
          'guidelines.form.title.create': 'Create New Guideline',
          'guidelines.form.title.edit': 'Edit Guideline',
          'contractType.loading': 'Loading contract types...',
        };
        return translations[key] || key;
      },
    }),
  };
});

// Mock useGuidelines hook
const mockUseGuidelines = {
  guidelines: [] as Guideline[],
  loading: false,
  error: null as string | null,
  loadGuidelines: vi.fn(),
  createNewGuideline: vi.fn(),
  updateExistingGuideline: vi.fn(),
  deleteExistingGuideline: vi.fn(),
  clearError: vi.fn(),
};

vi.mock('../../hooks/useGuidelines', () => ({
  useGuidelines: () => mockUseGuidelines,
}));

// Mock sonner
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

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

const mockGuidelines: Guideline[] = [
  {
    contractTypeId: 'service-agreement',
    clauseTypeId: 'payment-terms',
    name: 'Payment Terms',
    standardWording: 'Payment shall be made within 30 days',
    level: 'high',
    evaluationQuestions: ['Are payment terms clearly defined?'],
    examples: ['Payment due within 30 days of invoice'],
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
];

// Wrapper component to provide router context
const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <MemoryRouter>
    {children}
  </MemoryRouter>
);

describe('ContractTypeGuidelines', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset mock hook state
    mockUseGuidelines.guidelines = [];
    mockUseGuidelines.loading = false;
    mockUseGuidelines.error = null;
    // Set default params
    mockUseParams.mockReturnValue({ contractTypeId: 'service-agreement' });
  });

  it('renders loading state initially', () => {
    mockGetContractType.mockImplementation(() => new Promise(() => { })); // Never resolves

    render(
      <TestWrapper>
        <ContractTypeGuidelines />
      </TestWrapper>
    );

    expect(screen.getByText('Guidelines Management')).toBeInTheDocument();
    // Check for loading spinner instead of text
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders contract type guidelines after loading', async () => {
    mockGetContractType.mockResolvedValue(mockContractType);
    mockUseGuidelines.guidelines = mockGuidelines;

    render(
      <TestWrapper>
        <ContractTypeGuidelines />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Guidelines for Service Agreement')).toBeInTheDocument();
      expect(screen.getByText('Standard service agreement contract')).toBeInTheDocument();
      expect(screen.getByText('Payment Terms')).toBeInTheDocument();
    });
  });

  it('shows back button that navigates to contract types', async () => {
    mockGetContractType.mockResolvedValue(mockContractType);

    render(
      <TestWrapper>
        <ContractTypeGuidelines />
      </TestWrapper>
    );

    await waitFor(() => {
      // Find the back button by looking for the button with ArrowLeftIcon
      const backButtons = screen.getAllByRole('button');
      const backButton = backButtons.find(button =>
        button.querySelector('svg') &&
        button.querySelector('path[d="m12 19-7-7 7-7"]')
      );
      expect(backButton).toBeInTheDocument();
      fireEvent.click(backButton!);
    });

    expect(mockNavigate).toHaveBeenCalledWith('/contract-types');
  });

  it('shows create guideline button', async () => {
    mockGetContractType.mockResolvedValue(mockContractType);

    render(
      <TestWrapper>
        <ContractTypeGuidelines />
      </TestWrapper>
    );

    await waitFor(() => {
      const createButtons = screen.getAllByText('Create Guideline');
      expect(createButtons.length).toBeGreaterThan(0);
    });
  });

  it('opens create modal when create button is clicked', async () => {
    mockGetContractType.mockResolvedValue(mockContractType);

    render(
      <TestWrapper>
        <ContractTypeGuidelines />
      </TestWrapper>
    );

    await waitFor(() => {
      const createButtons = screen.getAllByText('Create Guideline');
      // Click the first create button (the one in the header)
      fireEvent.click(createButtons[0]);
    });

    expect(screen.getByText('Create New Guideline')).toBeInTheDocument();
  });

  it('displays empty state when no guidelines exist', async () => {
    mockGetContractType.mockResolvedValue(mockContractType);
    mockUseGuidelines.guidelines = [];

    render(
      <TestWrapper>
        <ContractTypeGuidelines />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('No Guidelines Found')).toBeInTheDocument();
    });
  });

  it('displays error state when contract type loading fails', async () => {
    const errorMessage = 'Contract type not found';
    mockGetContractType.mockRejectedValue(new Error(errorMessage));

    render(
      <TestWrapper>
        <ContractTypeGuidelines />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText(/Contract type not found/)).toBeInTheDocument();
      expect(screen.getByText('Back to Contract Types')).toBeInTheDocument();
    });
  });

  it('displays guidelines error when guidelines loading fails', async () => {
    mockGetContractType.mockResolvedValue(mockContractType);
    mockUseGuidelines.error = 'Failed to load guidelines';

    render(
      <TestWrapper>
        <ContractTypeGuidelines />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Guidelines for Service Agreement')).toBeInTheDocument();
      expect(screen.getByText(/Failed to load guidelines/)).toBeInTheDocument();
    });
  });

  it('shows contract type information in header', async () => {
    mockGetContractType.mockResolvedValue(mockContractType);

    render(
      <TestWrapper>
        <ContractTypeGuidelines />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('Guidelines for Service Agreement')).toBeInTheDocument();
      expect(screen.getByText('Standard service agreement contract')).toBeInTheDocument();
      expect(screen.getByText('ID: service-agreement')).toBeInTheDocument();
    });
  });

  it('hides contract type filter in guidelines filters', async () => {
    mockGetContractType.mockResolvedValue(mockContractType);

    render(
      <TestWrapper>
        <ContractTypeGuidelines />
      </TestWrapper>
    );

    await waitFor(() => {
      // Should not show contract type selection since we're in a specific contract type context
      expect(screen.queryByText('Select a contract type to manage guidelines')).not.toBeInTheDocument();
    });
  });

  it('handles invalid contract type ID', async () => {
    mockUseParams.mockReturnValue({ contractTypeId: undefined });

    render(
      <TestWrapper>
        <ContractTypeGuidelines />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText(/Contract type ID is required/)).toBeInTheDocument();
    });
  });

  it('calls loadGuidelines with correct parameters', async () => {
    mockGetContractType.mockResolvedValue(mockContractType);

    render(
      <TestWrapper>
        <ContractTypeGuidelines />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(mockUseGuidelines.loadGuidelines).toHaveBeenCalledWith('service-agreement', {
        search: '',
        level: '',
      });
    });
  });
});