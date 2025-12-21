## The Stock Archive

### Project Overview

An automated system to download and validate annual reports for Swedish OMXS30 companies (2019-2024). The pipeline discovers investor relations URLs, downloads reports, and validates them for completeness.

**Status**: ✅ Core pipeline complete with validation feedback loop

### Workflow

**IMPORTANT: Always check what's missing before downloading!**

#### Using CLI Commands (Recommended)

After installation with `pip install -e .`, use the clean CLI commands:

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

# Step 2: Download reports (only fetches missing ones)
aspiratio-download

# Step 3: Validate downloaded PDFs
aspiratio-validate

# Step 4: Update coverage table
aspiratio-update

# Step 5: Retry failures with smart logic (Playwright fallback)
aspiratio-retry

# Interactive UI
streamlit run scripts/app.py
```

#### Using Python Scripts (Alternative)

```bash
# Traditional method still works
python scripts/download_reports.py
python scripts/validate_reports.py
python scripts/update_coverage_table.py
python scripts/redownload_failed.py
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

**Setup:**
```bash
# Clone and navigate to project
cd aspiratio

# Install in editable mode (includes all dependencies)
pip install -e .

# Install Playwright browser
playwright install webkit

# Configuration is in config.yaml
# See CONFIG_GUIDE.md for details on using the config system
```

**Available CLI Commands:**
```bash
# Main workflow
aspiratio-download      # Batch download missing reports
aspiratio-validate      # Validate downloaded PDFs
aspiratio-retry         # Smart retry with Playwright fallback
aspiratio-update        # Update coverage table

# Setup tools (one-time)
aspiratio-build-master  # Build/validate instrument master
aspiratio-find-ir       # Find IR URLs for companies

# Interactive
streamlit run scripts/app.py  # Web UI for manual review
```

**Configuration:**
The project uses centralized configuration in `config.yaml`:
- Validation thresholds (min/max pages, confidence)
- Download parameters (retries, timeouts, rate limiting)
- HTTP settings (user agents)
- File paths
- Playwright settings

See [CONFIG_GUIDE.md](CONFIG_GUIDE.md) for usage examples.

**Testing individual companies:**
```python
from aspiratio.utils.report_downloader import download_annual_reports
from aspiratio.config import get_target_years

# Download reports for a specific company
download_annual_reports(
    ir_url="https://www.company.com/investors",
    company_name="Company Name",
    company_id="S1",
    years=get_target_years()  # From config
)
```

### Project Structure

```
aspiratio/
├── config.yaml                  # 🆕 Centralized configuration
├── requirements.txt             # 🆕 Python dependencies
├── CONFIG_GUIDE.md              # 🆕 Configuration usage guide
├── coverage_table_updated.csv   # Download tracking with priorities
├── validation_results.csv       # PDF validation feedback
├── instrument_master.csv        # Company database
├── omxs30_members.csv          # OMXS30 companies
├── aspiratio/
│   ├── config.py               # 🆕 Configuration loader
│   └── utils/              
│       ├── report_downloader.py     # Tier 1: Traditional scraping
│       ├── playwright_downloader.py # Tier 2: JavaScript sites
│       ├── ir_search.py             # IR URL discovery
│       ├── name_match.py            # Company name matching
│       └── io.py                    # File operations
├── scripts/                      
│   ├── download_reports.py      # Main batch downloader
│   ├── validate_reports.py      # PDF validation pipeline
│   ├── redownload_failed.py     # Smart retry with Playwright fallback
│   ├── app.py                   # Streamlit UI
│   ├── record_download.py       # Tier 3: Record manual downloads
│   ├── ir_scraper.py            # Find IR URLs
│   ├── build_master.py          # Build instrument master
│   └── update_coverage_table.py # Update coverage tracking
```

### Three-Tier Download Strategy

**Tier 1: Traditional Scraping** (Primary - 80%+ success)
- Searches IR pages for PDF links (HTML, JSON-LD, navigation)
- Failsafe: Main site → IR discovery if initial search fails
- Handles direct patterns for predictable sites

**Tier 2: Playwright/JavaScript** (Fallback - 10-15%)
- For sites with dynamic content (cookie popups, dropdowns)
- Registry-based: Record once, reuse for all years
- Currently implemented: Atlas Copco (S6)

**Tier 3: Manual Recording** (Last Resort - <5%)
- Streamlit app generates Playwright codegen commands
- User demonstrates download path once
- Agent analyzes and integrates pattern

The system automatically escalates: Tier 1 → Tier 2 → Tier 3
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



