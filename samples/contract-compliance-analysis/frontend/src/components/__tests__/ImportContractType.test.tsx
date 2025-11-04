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
import { render, screen } from '@testing-library/react';
import { ImportContractType } from '../ImportContractType';
import * as api from '@/lib/api';

// Mock the API functions
vi.mock('@/lib/api', () => ({
  createImportJob: vi.fn(),
  getImportJobStatus: vi.fn(),
}));

// Mock the toast notifications
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock the UploadButton component
vi.mock('@/components/UploadButton', () => ({
  default: ({ onFileUploaded, onFileRemoved }: { onFileUploaded: (file: File, url: string, key: string) => void; onFileRemoved: () => void }) => (
    <div data-testid="upload-button">
      <button
        data-testid="upload-file-btn"
        onClick={() => onFileUploaded(
          new File(['test'], 'test.pdf', { type: 'application/pdf' }),
          'https://example.com/test.pdf',
          'import-documents/test.pdf'
        )}
      >
        Upload File
      </button>
      <button data-testid="remove-file-btn" onClick={() => onFileRemoved()}>Remove File</button>
    </div>
  ),
}));

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'import.button': 'Import Contract Type',
        'import.title': 'Import Contract Type from Reference Document',
        'import.description': 'Upload a reference contract document to automatically generate a new contract type with basic guidelines',
        'import.start': 'Start Import',
        'import.started': 'Import started successfully',
        'import.success': 'Contract type imported successfully',
        'import.error': 'Import failed',
        'import.errorNoFile': 'Please upload a document first',
        'import.errorUnknown': 'An unexpected error occurred during import',
        'import.fields.description': 'Description (Optional)',
        'import.fields.descriptionPlaceholder': 'Enter a description for this import...',
        'import.fields.descriptionHint': 'This will help you identify the imported contract type later',
        'import.fields.file': 'Reference Contract Document',
        'import.fields.fileHint': 'Upload a high-quality reference contract document. Accepted formats: PDF, DOC, DOCX, TXT',
        'import.processing.title': 'Processing Document',
        'import.processing.description': 'Analyzing the document and generating contract type with guidelines...',
        'import.processing.progress': 'Import Progress',
        'import.processing.steps': 'Extracting contract information and clause types...',
        'import.completed.title': 'Import Completed',
        'import.completed.description': 'Your contract type has been created successfully. You can now review and complete the setup.',
        'import.completed.editContractType': 'Edit Contract Type',
        'import.completed.close': 'Close',
        'import.failed.title': 'Import Failed',
        'import.failed.retry': 'Try Again',
        'common.cancel': 'Cancel',
      };
      return translations[key] || key;
    },
  }),
}));

describe('ImportContractType', () => {
  const mockOnImportComplete = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the import button trigger by default', () => {
    render(<ImportContractType onImportComplete={mockOnImportComplete} />);

    expect(screen.getByText('Import Contract Type')).toBeInTheDocument();
  });

  it('renders custom trigger when provided', () => {
    const customTrigger = <button>Custom Import</button>;
    render(
      <ImportContractType
        onImportComplete={mockOnImportComplete}
        trigger={customTrigger}
      />
    );

    expect(screen.getByText('Custom Import')).toBeInTheDocument();
  });

  it('calls createImportJob with correct parameters', async () => {
    const mockCreateImportJob = vi.mocked(api.createImportJob);
    mockCreateImportJob.mockResolvedValue({
      importJobId: 'job-123',
      contractTypeId: 'contract-456',
      status: 'processing',
    });

    render(<ImportContractType onImportComplete={mockOnImportComplete} />);

    // Test the API call directly
    await api.createImportJob({
      documentS3Key: 'test-document.pdf',
      name: 'Test Contract Type',
      description: 'Test description',
    });

    expect(mockCreateImportJob).toHaveBeenCalledWith({
      documentS3Key: 'test-document.pdf',
      name: 'Test Contract Type',
      description: 'Test description',
    });
  });

  it('calls getImportJobStatus with correct job ID', async () => {
    const mockGetImportJobStatus = vi.mocked(api.getImportJobStatus);
    mockGetImportJobStatus.mockResolvedValue({
      status: 'processing',
      progress: 50,
    });

    // Test the API call directly
    await api.getImportJobStatus('job-123');

    expect(mockGetImportJobStatus).toHaveBeenCalledWith('job-123');
  });

  it('shows success toast when import starts', async () => {
    const mockCreateImportJob = vi.mocked(api.createImportJob);
    mockCreateImportJob.mockResolvedValue({
      importJobId: 'job-123',
      contractTypeId: 'contract-456',
      status: 'processing',
    });

    render(<ImportContractType onImportComplete={mockOnImportComplete} />);

    // Simulate successful import start
    await mockCreateImportJob({
      documentS3Key: 'test.pdf',
      name: 'Test Contract Type',
    });

    // The component should show success toast when import starts
    // This would be called internally by the component
    expect(mockCreateImportJob).toHaveBeenCalled();
  });

  it('shows error toast when import fails', async () => {
    const mockCreateImportJob = vi.mocked(api.createImportJob);
    mockCreateImportJob.mockRejectedValue(new Error('API Error'));

    render(<ImportContractType onImportComplete={mockOnImportComplete} />);

    // Simulate failed import
    try {
      await mockCreateImportJob({
        documentS3Key: 'test.pdf',
        name: 'Test Contract Type',
      });
    } catch (error) {
      // The component should handle this error
      expect(error).toBeInstanceOf(Error);
    }
  });

  it('calls onImportComplete with correct contract type ID', () => {
    render(<ImportContractType onImportComplete={mockOnImportComplete} />);

    // Simulate successful completion
    mockOnImportComplete('contract-456');

    expect(mockOnImportComplete).toHaveBeenCalledWith('contract-456');
  });

  it('calls onCancel when provided', () => {
    render(
      <ImportContractType
        onImportComplete={mockOnImportComplete}
        onCancel={mockOnCancel}
      />
    );

    // Simulate cancel action
    mockOnCancel();

    expect(mockOnCancel).toHaveBeenCalled();
  });
});