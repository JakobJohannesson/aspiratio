# Atlas Copco (S6) Playwright Implementation

## Overview
Successfully implemented automated download for Atlas Copco annual reports using Playwright-recorded navigation patterns.

## Recording Details
**Date:** December 22, 2025  
**Company:** Atlas Copco AB (S6)  
**Year Tested:** 2024  
**Script Location:** `aspiratio/utils/playwright_scripts/S6_2024.py`

## Navigation Pattern Discovered

### Step 1: Cookie Consent
- Handled automatically: Click "Allow only necessary" button
- Locator: `.onetrust-pc-dark-filter` and button with name "Allow only necessary"

### Step 2: Navigate to Reports Section
- Click link: "Reports and presentations Download our financial documents"
- This takes to the financial documents page

### Step 3: Find Annual Report
- Look for link with pattern: "Annual Report {year} (PDF)"
- Extract href attribute (direct PDF link)
- URL pattern: `https://www.atlascopcogroup.com/content/dam/atlas-copco/group/documents/investors/financial-publications/english/YYYYMMDD-annual-report-{year}-incl-sustainability-report-and-corporate-governance-report-copy-of-the-official-ESEF-format.pdf.coredownload.inline.pdf`

## Implementation

### Function: `download_atlas_copco_report(year, output_dir)`
**Location:** `aspiratio/utils/playwright_downloader.py`

**Features:**
- Async function using Playwright
- Handles cookie consent automatically
- Navigates to Reports section
- Extracts PDF URL from link href
- Falls back to popup capture if needed
- Downloads and validates PDF
- Returns detailed result dict

**Test Results:**
```
✓ Successfully downloaded Atlas Copco 2024 Annual Report
  - Pages: 169
  - Size: 10.1 MB
  - PDF URL: Direct link from href attribute
  - Cookie consent handled: Yes
  - Navigation successful: Yes
```

### Integration with Redownload Script
**Location:** `scripts/redownload_failed.py`

**Changes:**
1. Added `from aspiratio.utils.playwright_downloader import PLAYWRIGHT_HANDLERS`
2. Added `import asyncio` for async execution
3. Added Playwright fallback in year_reports check:
   - When traditional search finds no reports
   - Checks if company ID (e.g., 'S6') is in PLAYWRIGHT_HANDLERS registry
   - Executes Playwright download
   - Validates result
   - Updates coverage table
   - Logs as 'success_playwright'

**Fallback Logic:**
```python
if not year_reports:
    # Traditional search failed
    if cid in PLAYWRIGHT_HANDLERS:
        # Try Playwright-based download
        playwright_result = asyncio.run(PLAYWRIGHT_HANDLERS[cid](year))
        # Validate and update coverage table
```

## Registry System
**Location:** `aspiratio/utils/playwright_downloader.py` (bottom of file)

```python
PLAYWRIGHT_HANDLERS = {
    'S6': download_atlas_copco_report,  # Atlas Copco AB
    # Add more as they're recorded:
    # 'S14': download_nibe_report,
    # 'S21': download_saab_report,
}
```

**How to add new companies:**
1. Record download using Streamlit app "Record Download" tab
2. Run: `playwright codegen --browser webkit --target python-async --output {path} {ir_url}`
3. Demonstrate download in browser
4. Share generated script
5. Create async function in `playwright_downloader.py` following Atlas Copco pattern
6. Add to PLAYWRIGHT_HANDLERS registry
7. Function will be automatically used as fallback in redownload script

## Key Learnings

### What Works
- **Direct href extraction**: Much more reliable than popup capture
- **Cookie consent handling**: Works with try/except for companies without consent
- **Specific link text**: "Annual Report {year} (PDF)" is company-specific but effective
- **Async pattern**: Clean integration with sync redownload script using asyncio.run()

### Common Patterns for Other Companies
1. **Cookie consent**: Most Swedish companies use OneTrust or similar
2. **Reports section**: Usually in footer or top navigation
3. **Year-specific links**: Look for text pattern matching year
4. **PDF URLs**: Extract from href attribute before clicking
5. **Direct links**: Many companies use direct PDF links (not popups)

## Next Steps

### High Priority Companies for Recording
Companies with 0% success rate that need Playwright:
1. **NIBE (S14)** - 0/6 reports
2. **SAAB (S21)** - 0/6 reports
3. **SEB (S22)** - 0/6 reports
4. **SKF (S24)** - 0/6 reports
5. **Handelsbanken (S28)** - 0/6 reports
6. **Telia (S2)** - 0/6 reports
7. **Volvo Car (S8)** - 0/6 reports

### Recording Workflow
1. Select company in Streamlit app
2. Copy command: `playwright codegen --browser webkit --target python-async --output {path} {ir_url}`
3. Run in terminal
4. Demonstrate download for one year (e.g., 2024)
5. Share generated script content
6. Agent will analyze and implement

### Pattern Library Growth
As more companies are recorded, common patterns will emerge:
- Standard cookie consent handlers
- Common navigation structures
- Typical report page layouts
- Reusable selector patterns

This will enable creating more generalized functions and potentially automatic pattern detection.

## Files Modified
- ✅ `aspiratio/utils/playwright_downloader.py` - Added Atlas Copco handler
- ✅ `scripts/redownload_failed.py` - Added Playwright fallback logic
- ✅ `companies/S6/annual_report_2024.pdf` - Downloaded successfully (169 pages, 10.1 MB)

## Validation
- [x] Script executes without errors
- [x] PDF downloads successfully
- [x] File size > 1MB (10.1 MB ✓)
- [x] Page count >= 50 (169 pages ✓)
- [x] Integration with redownload script
- [x] Registry system functional
- [x] Async execution works

## Success Rate Impact
Before implementation:
- Atlas Copco (S6): 0/6 reports (0%)
- Overall: 67/138 (48.6%)

After implementation:
- Atlas Copco (S6): 1/6 reports (16.7%) - will improve as more years are added
- Expected after full run: 73/138+ (52.9%+)

**Note:** Once Atlas Copco handler is run for all years 2019-2024, success rate will increase further. Currently only 2024 has been tested.
