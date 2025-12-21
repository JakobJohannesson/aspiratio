## The Stock Archive

### Project Overview

**Status**: ✅ Core pipeline complete with validation

The system successfully downloads and validates annual reports for Swedish OMXS30 companies (2019-2024). Currently **50 out of 72** downloaded PDFs pass validation (69.4% success rate).

**Completed:**
- ✅ IR URL discovery and validation
- ✅ Automated annual report downloader
- ✅ PDF validation with company/year verification
- ✅ Pattern learning from successful downloads
- ✅ Direct URL patterns for JavaScript-heavy sites (ASSA ABLOY)
- ✅ Quarterly/interim report filtering
- ✅ Coverage tracking with Streamlit feedback UI

**Top Performing Companies** (use as pattern examples):
- AstraZeneca: 6/6 reports validated (100% confidence)
- Addtech: 6/6 reports validated (73% confidence)
- Hexagon: 5/6 reports validated (97% confidence)
- Lifco: 5/6 reports validated (84% confidence)
- Ericsson: 4/6 reports validated (100% confidence)






An automated system to collect annual reports for Swedish OMXS30 companies (2019-2024). The pipeline discovers investor relations URLs, validates them, and downloads historical annual reports for analysis.

**Status**: ✅ Core implementation complete

### Quick Start

```bash
# 1. Find IR URLs for all companies
python scripts/ir_scraper.py

# 2. Validate URLs (opens Streamlit UI)
streamlit run scripts/app.py

# 3. Download annual reports
python scripts/download_reports.py

# 4. Validate downloaded PDFs
python scripts/validate_reports.py
```

This will:
- Download reports to `companies/{CID}/`
- Validate each PDF (min 50 pages, company name, year verification)
- Copy valid reports to `companies_validated/{CID}/`
- Generate `validation_results.csv` with detailed feedback

### Features

- **Intelligent IR URL Discovery**: Multi-query search with sophisticated scoring (domain matching, path analysis, content inspection)
- **URL Simplification**: Automatically strips deep links to find root IR pages
- **Flexible Report Detection**: Handles direct PDF links and dynamic download URLs
- **Recursive Search**: Follows navigation links (up to 2 levels deep) to find report pages
- **Smart Filtering**: Excludes quarterly/interim reports, SEC filings, and other non-annual documents
- **Validation Pipeline**: Verifies page count (min 50), company name presence, and year mentions in PDF content
- **Pattern Learning**: Identifies successful download patterns from validated reports for future improvements
- **Direct URL Patterns**: Handles JavaScript-heavy sites (ASSA ABLOY) with predictable URL structures
- **Progress Tracking**: Detailed logging, JSON summaries, and CSV validation reports
- **Encrypted PDF Support**: Handles password-protected PDFs with PyCryptodome
- **Smart Skipping**: Won't re-download existing reports

### Known Limitations

- **JavaScript-Rendered Content**: Some companies (ABB Group Annual Reports) use JavaScript with unpredictable URL hashes. Requires manual intervention or Playwright integration.
- **Company-Specific Patterns**: Each company may have unique document structures requiring custom handling
- **Validation Edge Cases**: Some reports (Boliden, Epiroc) don't consistently mention the year in early pages

### Current Success Rate

**Overall**: 50/72 PDFs validated (69.4%)

**By Company Type**:
- Perfect (6/6): AstraZeneca, Addtech
- Excellent (5/6): Hexagon, Lifco
- Good (4+/6): Ericsson, Essity, Evolution, Sandvik, Tele2, Boliden
- Needs Work: ABB Ltd (1/7), Atlas Copco (0/5 - downloading quarterly reports)

### Supported IR Page Structures

✅ **Works well with:**
- Direct PDF links in HTML (e.g., Addtech: `/fileadmin/user_upload/Arsredovisningar/Addtech-Annual-Report-24-25.pdf`)
- Dynamic download URLs (e.g., Swedbank: `?download=...&id=...`)
- Static HTML-based document libraries
- Fiscal year formats: 2024, 24-25, 2024-25
- Multi-level navigation (up to 2 levels deep)
- Cross-subdomain links (e.g., global.abb.com → library.e.abb.com)

❌ **Currently limited support:**
- JavaScript/AJAX-loaded content (ABB's annual-reporting-suite)
- Interactive document selectors
- Login-required sections

### Project Structure

```
aspiratio/
├── instrument_master.csv          # Core database
├── omxs30_members.csv            # OMXS30 reference list
├── validation_results.csv        # PDF validation feedback
├── coverage_table_updated.csv    # Download attempt tracking
├── aspiratio/utils/              
│   ├── io.py                     # File I/O
│   ├── ir_search.py              # IR URL discovery
│   └── report_downloader.py      # Annual report scraper (50+ page filter)
├── scripts/                      
│   ├── ir_scraper.py            # Batch IR URL finder
│   ├── app.py                   # Validation UI (Streamlit)
│   ├── download_reports.py      # Batch downloader
│   ├── validate_reports.py      # PDF validation & pattern learning
│   └── update_coverage_table.py # Generate coverage reports
├── companies/{CID}/              # Downloaded reports
│   └── annual_report_{year}.pdf
└── companies_validated/{CID}/    # Validated reports only
    └── annual_report_{year}.pdf
```



### Usage

#### Step 1: Find Investor Relations URLs
```bash
# Run IR scraper to find URLs for all companies
python scripts/ir_scraper.py
```

#### Step 2: Validate URLs
```bash
# Launch Streamlit app for manual validation
streamlit run scripts/app.py
```

#### Step 3: Download Annual Reports
```bash
# Download reports for all validated companies
python scripts/download_reports.py
```

The script will:
- Process all companies with validated IR URLs
- Search for annual reports from 2019-2024
- Download PDFs to `companies/{CID}/annual_report_{year}.pdf`
- Validate each PDF has at least 10 pages
- Skip reports that already exist
- Generate a summary JSON file with download results

