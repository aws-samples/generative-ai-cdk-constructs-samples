# Frontend Contract Type Tests

This directory contains unit tests for the contract type functionality.

## Test Files

- `ContractTypeSelect.test.tsx` - Tests for the ContractTypeSelect component
- `NewAnalysisModal.test.tsx` - Tests for the updated NewAnalysisModal component

## Running Tests

To run these tests, you'll need to install the testing dependencies first:

```bash
npm install --save-dev vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

Then run:

```bash
npm test
```

## Test Coverage

The tests cover:

### ContractTypeSelect Component
- ✅ Loading state display
- ✅ Contract types loading and filtering (active only)
- ✅ Auto-selection of single contract type
- ✅ Selection change handling
- ✅ Error state handling
- ✅ Empty state handling
- ✅ Required field indicator
- ✅ Disabled state
- ✅ Selected value display

### NewAnalysisModal Component
- ✅ Modal trigger and opening
- ✅ Form field rendering
- ✅ Submit button state management
- ✅ Form submission with contract type
- ✅ Constitutional check inclusion
- ✅ Loading state during submission
- ✅ Form reset after successful submission
- ✅ Error handling (modal stays open on failure)
- ✅ File upload and removal

## Manual Testing

You can also test the components manually by:

1. Starting the development server: `npm run dev`
2. Opening the application in a browser
3. Testing the "New Analysis" button to verify contract type selection
4. Testing the jobs list to verify contract type filtering
5. Testing job details to verify contract type display