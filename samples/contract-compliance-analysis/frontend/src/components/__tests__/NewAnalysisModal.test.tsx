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
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { NewAnalysisModal } from '../NewAnalysisModal';
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
        'newAnalysis.button': 'New Analysis',
        'newAnalysis.title': 'New Contract Analysis',
        'newAnalysis.description': 'Create a new compliance analysis',
        'newAnalysis.create': 'Create',
        'newAnalysis.creating': 'Creating...',
        'newAnalysis.fields.description': 'Description',
        'newAnalysis.fields.descriptionPlaceholder': 'Enter a description for this analysis',
        'newAnalysis.fields.file': 'Contract Upload',
        'newAnalysis.fields.fileTooltip': 'Accepted formats: PDF, DOC, DOCX, TXT files',
        'newAnalysis.fields.reportLanguage': 'Report Language',
        'newAnalysis.fields.constitutionalCheck': 'Constitutional Check',
        'newAnalysis.fields.constitutionalCheckDescription': 'Enable optional constitutional compliance check',
        'contractType.label': 'Contract Type',
        'contractType.placeholder': 'Select a contract type',
        'languages.en': 'English',
        'languages.es': 'Spanish',
        'languages.pt_BR': 'Portuguese (Brazil)',
        'common.cancel': 'Cancel',
        'common.active': 'Active',
      };
      return translations[key] || key;
    },
    i18n: {
      language: 'en',
    },
  }),
  initReactI18next: {
    type: '3rdParty',
    init: vi.fn(),
  },
}));

// Mock UploadButton component
vi.mock('../UploadButton', () => ({
  default: ({ onFileUploaded, onFileRemoved }: { onFileUploaded: (file: File | null, error: Error | null, s3Key: string) => void; onFileRemoved: () => void }) => (
    <div data-testid="upload-button">
      <button
        onClick={() => onFileUploaded(null, null, 'test-s3-key')}
        data-testid="mock-upload"
      >
        Upload File
      </button>
      <button
        onClick={() => onFileRemoved()}
        data-testid="mock-remove"
      >
        Remove File
      </button>
    </div>
  ),
}));

// Mock ContractTypeSelect component
vi.mock('../ContractTypeSelect', () => ({
  ContractTypeSelect: ({ value, onChange, required }: { value: string; onChange: (value: string) => void; required?: boolean }) => (
    <div data-testid="contract-type-select">
      <label>
        Contract Type {required && '*'}
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          data-testid="contract-type-dropdown"
        >
          <option value="">Select a contract type</option>
          <option value="service-agreement">Service Agreement</option>
          <option value="employment-contract">Employment Contract</option>
        </select>
      </label>
    </div>
  ),
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
];

describe('NewAnalysisModal', () => {
  const mockOnSubmit = vi.fn();
  const user = userEvent.setup();

  beforeEach(() => {
    vi.clearAllMocks();
    mockGetContractTypes.mockResolvedValue(mockContractTypes);
  });

  it('renders trigger button', () => {
    render(<NewAnalysisModal onSubmit={mockOnSubmit} />);

    expect(screen.getByText('New Analysis')).toBeInTheDocument();
  });

  it('opens modal when trigger button is clicked', async () => {
    render(<NewAnalysisModal onSubmit={mockOnSubmit} />);

    await user.click(screen.getByText('New Analysis'));

    expect(screen.getByText('New Contract Analysis')).toBeInTheDocument();
    expect(screen.getByText('Create a new compliance analysis')).toBeInTheDocument();
  });

  it('renders all form fields', async () => {
    render(<NewAnalysisModal onSubmit={mockOnSubmit} />);

    await user.click(screen.getByText('New Analysis'));

    expect(screen.getByLabelText(/Description/)).toBeInTheDocument();
    expect(screen.getByTestId('upload-button')).toBeInTheDocument();
    expect(screen.getByTestId('contract-type-select')).toBeInTheDocument();
    expect(screen.getAllByRole('combobox')).toHaveLength(2); // Contract type and language selects
    expect(screen.getByRole('switch')).toBeInTheDocument(); // Constitutional check
  });

  it('disables submit button when required fields are missing', async () => {
    render(<NewAnalysisModal onSubmit={mockOnSubmit} />);

    await user.click(screen.getByText('New Analysis'));

    const submitButton = screen.getByText('Create');
    expect(submitButton).toBeDisabled();
  });

  it('enables submit button when all required fields are filled', async () => {
    render(<NewAnalysisModal onSubmit={mockOnSubmit} />);

    await user.click(screen.getByText('New Analysis'));

    // Fill description
    await user.type(screen.getByLabelText(/Description/), 'Test description');

    // Upload file
    await user.click(screen.getByTestId('mock-upload'));

    // Select contract type
    await user.selectOptions(screen.getByTestId('contract-type-dropdown'), 'service-agreement');

    await waitFor(() => {
      const submitButton = screen.getByText('Create');
      expect(submitButton).not.toBeDisabled();
    });
  });

  it('calls onSubmit with correct data when form is submitted', async () => {
    mockOnSubmit.mockResolvedValue(undefined);

    render(<NewAnalysisModal onSubmit={mockOnSubmit} />);

    await user.click(screen.getByText('New Analysis'));

    // Fill form
    await user.type(screen.getByLabelText(/Description/), 'Test description');
    await user.click(screen.getByTestId('mock-upload'));
    await user.selectOptions(screen.getByTestId('contract-type-dropdown'), 'service-agreement');

    // Submit form
    await user.click(screen.getByText('Create'));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        documentS3Key: 'test-s3-key',
        description: 'Test description',
        contractTypeId: 'service-agreement',
        reportLanguage: 'en',
        constitutionalCheck: false,
      });
    });
  });

  it('includes constitutional check when enabled', async () => {
    mockOnSubmit.mockResolvedValue(undefined);

    render(<NewAnalysisModal onSubmit={mockOnSubmit} />);

    await user.click(screen.getByText('New Analysis'));

    // Fill form and enable constitutional check
    await user.type(screen.getByLabelText(/Description/), 'Test description');
    await user.click(screen.getByTestId('mock-upload'));
    await user.selectOptions(screen.getByTestId('contract-type-dropdown'), 'service-agreement');
    await user.click(screen.getByRole('switch'));

    // Submit form
    await user.click(screen.getByText('Create'));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        documentS3Key: 'test-s3-key',
        description: 'Test description',
        contractTypeId: 'service-agreement',
        reportLanguage: 'en',
        constitutionalCheck: true,
      });
    });
  });

  it('shows loading state during submission', async () => {
    mockOnSubmit.mockImplementation(() => new Promise(() => {})); // Never resolves

    render(<NewAnalysisModal onSubmit={mockOnSubmit} />);

    await user.click(screen.getByText('New Analysis'));

    // Fill form
    await user.type(screen.getByLabelText(/Description/), 'Test description');
    await user.click(screen.getByTestId('mock-upload'));
    await user.selectOptions(screen.getByTestId('contract-type-dropdown'), 'service-agreement');

    // Submit form
    await user.click(screen.getByText('Create'));

    await waitFor(() => {
      expect(screen.getByText('Creating...')).toBeInTheDocument();
    });
  });

  it('resets form and closes modal after successful submission', async () => {
    mockOnSubmit.mockResolvedValue(undefined);

    render(<NewAnalysisModal onSubmit={mockOnSubmit} />);

    await user.click(screen.getByText('New Analysis'));

    // Fill form
    await user.type(screen.getByLabelText(/Description/), 'Test description');
    await user.click(screen.getByTestId('mock-upload'));
    await user.selectOptions(screen.getByTestId('contract-type-dropdown'), 'service-agreement');

    // Submit form
    await user.click(screen.getByText('Create'));

    await waitFor(() => {
      // Modal should be closed (title not visible)
      expect(screen.queryByText('New Contract Analysis')).not.toBeInTheDocument();
    });
  });

  it('keeps modal open when submission fails', async () => {
    mockOnSubmit.mockRejectedValue(new Error('Submission failed'));

    render(<NewAnalysisModal onSubmit={mockOnSubmit} />);

    await user.click(screen.getByText('New Analysis'));

    // Fill form
    await user.type(screen.getByLabelText(/Description/), 'Test description');
    await user.click(screen.getByTestId('mock-upload'));
    await user.selectOptions(screen.getByTestId('contract-type-dropdown'), 'service-agreement');

    // Submit form
    await user.click(screen.getByText('Create'));

    await waitFor(() => {
      // Modal should still be open
      expect(screen.getByText('New Contract Analysis')).toBeInTheDocument();
    });
  });

  it('removes uploaded file when remove button is clicked', async () => {
    render(<NewAnalysisModal onSubmit={mockOnSubmit} />);

    await user.click(screen.getByText('New Analysis'));

    // Upload file first
    await user.click(screen.getByTestId('mock-upload'));

    // Remove file
    await user.click(screen.getByTestId('mock-remove'));

    // Submit button should be disabled again
    const submitButton = screen.getByText('Create');
    expect(submitButton).toBeDisabled();
  });
});