## The Stock Archive

### Project Overview

An automated system to download and validate annual reports for Swedish OMXS30 companies (2019-2024). The pipeline discovers investor relations URLs, downloads reports, and validates them for completeness.

**Status**: ✅ Core pipeline complete with validation feedback loop

### Workflow

```bash
# 1. Download annual reports for all companies
python scripts/download_reports.py

# 2. Validate downloaded PDFs
python scripts/validate_reports.py

# 3. Review validation results
# Check coverage_table_updated.csv for Milestone 4 status and Priority column

# 4. Re-download failed reports with better patterns
python scripts/redownload_failed.py
```

**What happens:**
- Downloads reports to `companies/{CID}/` (min 50 pages, excludes quarterly/SEC filings)
- Validates each PDF (company name, year verification)
- Copies valid reports to `companies_validated/{CID}/`
- Updates `coverage_table_updated.csv` with priorities: "Complete ✓", "Needs Work ⚠", "Not Downloaded"

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



