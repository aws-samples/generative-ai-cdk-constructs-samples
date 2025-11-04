# Mock Data for Testing

Mock data for testing key status scenarios and UI validation in the compliance analysis system.

## Quick Start

1. Copy the environment template:

   ```bash
   cp .env.local.example .env.local
   ```

2. Enable mock data in `.env.local`:

   ```env
   VITE_ENABLE_MOCK_JOBS=true
   ```

3. Start development server:
   ```bash
   pnpm run dev
   ```

## What You Get

### Mock Jobs

- **14 test scenarios** covering key status combinations
- Jobs with and without legislation checks
- Various compliance states (compliant, non-compliant, mixed)
- All processing states (RUNNING, SUCCEEDED, FAILED, TIMED_OUT, ABORTED)

## Where Mock Data Appears

✅ **Home page filters**: Mock Contract option available  
✅ **Job details**: Including top-page indicator for mock jobs  
✅ **Table**: Including badges for mocked items contract types  
❌ **New Analysis Modal**: Clean, no mock options  
❌ **Contract Type Management**: Clean, no mock data

### Status Colors

- 🟢 **Green**: Success/Compliant
- 🟡 **Amber**: Guidelines non-compliant
- 🔴 **Red**: Legislation non-compliant
- ⚪ **Gray**: Technical failures
- 🔵 **Blue**: Processing (with tooltips)

## Important Notes

- **Never commit your `.env.local`**
- `.env.local` is gitignored by default
- Mock jobs show complete analysis data (Faker-generated clauses)
- Console logs indicate when mock is active

## Disabling Mock Data

Set `VITE_ENABLE_MOCK_JOBS=false` in `.env.local` or remove the line entirely.
