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
import { BrowserRouter } from 'react-router';
import { ContractTypeManagement } from '@/components/ContractTypeManagement';
import * as api from '@/lib/api';
import type { ContractType } from '@/lib/types';

// Mock the API functions
vi.mock('@/lib/api');
const mockApi = vi.mocked(api);

// Mock react-router hooks
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
          'contractType.management.activate': 'Activate',
          'contractType.management.deactivate': 'Deactivate',
          'contractType.form.name': 'Name',
          'contractType.form.description': 'Description',
          'guidelines.import.status.imported': 'Imported',
          'guidelines.import.status.needsReview': 'Needs Review',
          'guidelines.import.status.activate': 'Activate Contract Type',
          'import.button': 'Import Contract Type',
        };
        return translations[key] || key;
      },
    }),
  };
});

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const mockImportedContractType: ContractType = {
  contractTypeId: 'imported-contract-type-1',
  name: 'Service Agreement (Imported)',
  description: 'Professional services agreement imported from reference document',
  companyPartyType: 'Customer',
  otherPartyType: 'Service Provider',
  highRiskThreshold: 0,
  mediumRiskThreshold: 1,
  lowRiskThreshold: 3,
  isActive: false,
  defaultLanguage: 'en',
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
  isImported: true,
  importSourceDocument: 'contracts/service-agreement-template.pdf',
};

const mockActiveContractType: ContractType = {
  ...mockImportedContractType,
  contractTypeId: 'active-contract-type-1',
  name: 'Service Agreement (Active)',
  isActive: true,
  isImported: false,
};

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

describe('Contract Type Import Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApi.getContractTypes.mockResolvedValue([mockImportedContractType, mockActiveContractType]);
    mockApi.updateContractType.mockResolvedValue({ ...mockImportedContractType, isActive: true });
  });

  describe('ContractTypeManagement with imported types', () => {
    it('should display visual indicators for imported contract types', async () => {
      renderWithProviders(<ContractTypeManagement />);

      await waitFor(() => {
        expect(screen.getByText('Service Agreement (Imported)')).toBeInTheDocument();
      });

      // Check for imported badge
      expect(screen.getByText('Imported')).toBeInTheDocument();

      // Check for needs review indicator
      expect(screen.getByText('Needs Review')).toBeInTheDocument();

      // Check for source document info
      expect(screen.getByText('Source: service-agreement-template.pdf')).toBeInTheDocument();
    });

    it('should show activate button for imported inactive contract types', async () => {
      renderWithProviders(<ContractTypeManagement />);

      await waitFor(() => {
        expect(screen.getByText('Service Agreement (Imported)')).toBeInTheDocument();
      });

      // Check for activate button with special styling (get the one in the table row)
      const activateButtons = screen.getAllByRole('button', { name: /activate/i });
      const tableActivateButton = activateButtons.find(button =>
        button.classList.contains('bg-green-50')
      );
      expect(tableActivateButton).toBeInTheDocument();
      expect(tableActivateButton).toHaveClass('bg-green-50');
    });

    it('should handle contract type activation', async () => {
      renderWithProviders(<ContractTypeManagement />);

      await waitFor(() => {
        expect(screen.getByText('Service Agreement (Imported)')).toBeInTheDocument();
      });

      const activateButtons = screen.getAllByRole('button', { name: /activate/i });
      const tableActivateButton = activateButtons.find(button =>
        button.classList.contains('bg-green-50')
      );
      fireEvent.click(tableActivateButton!);

      await waitFor(() => {
        expect(mockApi.updateContractType).toHaveBeenCalledWith(
          'imported-contract-type-1',
          {
            name: 'Service Agreement (Imported)',
            description: 'Professional services agreement imported from reference document',
            companyPartyType: 'Customer',
            otherPartyType: 'Service Provider',
            highRiskThreshold: 0,
            mediumRiskThreshold: 1,
            lowRiskThreshold: 3,
            defaultLanguage: 'en',
            isActive: true
          }
        );
      });
    });

    it('should show import button', async () => {
      renderWithProviders(<ContractTypeManagement />);

      await waitFor(() => {
        expect(screen.getByText('Import Contract Type')).toBeInTheDocument();
      });
    });
  });

  // Note: More comprehensive tests for ContractTypeGuidelines would require
  // mocking the useGuidelines hook and other dependencies. For now, we focus
  // on the ContractTypeManagement integration which is the main entry point.
});