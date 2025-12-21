## The Stock Archive

### Project Overview

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
```

### Features

- **Intelligent IR URL Discovery**: Multi-query search with sophisticated scoring (domain matching, path analysis, content inspection)
- **URL Simplification**: Automatically strips deep links to find root IR pages
- **Flexible Report Detection**: Handles direct PDF links and dynamic download URLs
- **Recursive Search**: Follows navigation links (up to 2 levels deep) to find report pages
- **Validation**: Ensures PDFs have minimum 10 pages, readable format
- **Progress Tracking**: Detailed logging and JSON summaries of all downloads
- **Smart Skipping**: Won't re-download existing reports

### Known Limitations

- **JavaScript-Rendered Content**: Some companies (ABB) use JavaScript to dynamically load annual reports. The current implementation only parses static HTML.
- **Workaround**: For these cases, manually download PDFs and place them in `companies/{CID}/annual_report_{year}.pdf`

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
├── aspiratio/utils/              
│   ├── io.py                     # File I/O
│   ├── ir_search.py              # IR URL discovery
│   └── report_downloader.py      # Annual report scraper
├── scripts/                      
│   ├── ir_scraper.py            # Batch IR URL finder
│   ├── app.py                   # Validation UI
│   └── download_reports.py      # Batch downloader
└── companies/{CID}/              # Downloaded reports
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

