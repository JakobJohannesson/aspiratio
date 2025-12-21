## The Stock Archive

### Project Overview

An automated system to download and validate annual reports for Swedish OMXS30 companies (2019-2024). The pipeline discovers investor relations URLs, downloads reports, and validates them for completeness.

**Status**: ✅ Core pipeline complete with validation feedback loop

### Workflow

**IMPORTANT: Always check what's missing before downloading!**

```bash
# Step 1: Check what's missing from coverage table
python3 -c "
import pandas as pd
df = pd.read_csv('coverage_table_updated.csv', sep='\t')
missing = df[df['Priority'] != 'Complete ✓']
print(f'Missing: {len(missing)} reports')
by_company = missing.groupby('CompanyName').size().sort_values(ascending=False)
for company, count in by_company.items():
    print(f'  {company}: {count}')
"

# Step 2: Download reports (only fetches missing ones from coverage table)
python scripts/download_reports.py

# Step 3: Validate downloaded PDFs
python scripts/validate_reports.py

# Step 4: Review results - check coverage_table_updated.csv Priority column
# Repeat steps 2-3 for reports that still need work
```

**Key principles:**
- **Check first**: Always verify what's missing in coverage table before downloading
- **Download only missing**: Script automatically filters to Priority != "Complete ✓"
- **Validate immediately**: Each PDF is validated right after download
- **Update coverage**: Coverage table is updated after validation with status
- **Try alternatives**: If multiple PDFs found for a year, tries each until one validates

### Key Features

- **Smart Filtering**: Excludes quarterly/interim reports and SEC filings (Form 20-F, Form SD)
- **Validation Pipeline**: Verifies page count (50-500), company name, and year in PDF content
- **Priority System**: Automatic prioritization based on validation results
- **Pattern Learning**: Direct URL patterns for JavaScript-heavy sites (ASSA ABLOY)
- **Playwright Support**: Handles dynamic content for complex sites (ABB Group Annual Reports)
- **Encrypted PDFs**: Supports password-protected documents
- **Progress Tracking**: Coverage table with milestone tracking and priorities

### Current Challenges

- **JavaScript-Heavy Sites**: Some companies (ABB) require Playwright for dynamic content
- **Company-Specific Patterns**: Each company may have unique document structures
- **Year Detection**: Some reports don't consistently mention the year in early pages

### Development

**Dependencies:**
```bash
pip install pandas beautifulsoup4 requests PyPDF2 streamlit playwright pycryptodome
playwright install chromium
```

**Testing individual companies:**
```python
from aspiratio.utils.report_downloader import download_annual_reports

# Download reports for a specific company
download_annual_reports(
    ir_url="https://www.company.com/investors",
    company_name="Company Name",
    company_id="S1",
    years=[2019, 2020, 2021, 2022, 2023, 2024]
)
```

### Project Structure

```
aspiratio/
├── coverage_table_updated.csv    # Download tracking with priorities
├── validation_results.csv        # PDF validation feedback
├── instrument_master.csv         # Company database
├── omxs30_members.csv           # OMXS30 companies
├── aspiratio/utils/              
│   ├── report_downloader.py     # Core downloader (50+ pages, quarterly filter)
│   ├── playwright_downloader.py # JavaScript-heavy sites (ABB)
│   ├── ir_search.py             # IR URL discovery
│   ├── name_match.py            # Company name matching
│   └── io.py                    # File operations
├── scripts/                      
│   ├── download_reports.py      # Main download script
│   ├── validate_reports.py      # PDF validation pipeline
│   ├── redownload_failed.py     # Re-download with better patterns
│   ├── app.py                   # Streamlit UI for manual review
│   ├── ir_scraper.py            # Find IR URLs
│   ├── build_master.py          # Build instrument master
│   └── update_coverage_table.py # Update coverage tracking
├── companies/{CID}/              # Downloaded PDFs
└── companies_validated/{CID}/    # Validated PDFs only
```



