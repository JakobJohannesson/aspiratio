# Quick Start Guide - Running Aspiratio

## Current Status
**Progress:** 68/180 reports validated (37.8% complete)  
**Main Blocker:** No internet connectivity in current environment

---

## Prerequisites

```bash
# Install dependencies
pip install -e .

# Install Playwright browser (for JavaScript-heavy sites)
playwright install webkit
```

---

## Check Current Status

```bash
# View validated reports count
python3 -c "
import pandas as pd
v = pd.read_csv('validation_results.csv')
validated = len(v[v['Valid'] == True])
print(f'✓ Validated: {validated}/180 reports ({validated/180*100:.1f}%)')
"

# View missing reports by company
python3 -c "
import pandas as pd
df = pd.read_csv('coverage_table_updated.csv', sep='\t')
missing = df[df['Priority'] != 'Complete ✓']
print(f'Missing: {len(missing)} reports')
by_company = missing.groupby('CompanyName').size().sort_values(ascending=False)
for company, count in by_company.items():
    print(f'  {company}: {count}')
"
```

---

## Download Missing Reports

⚠️ **REQUIRES INTERNET CONNECTIVITY**

```bash
# Step 1: Sync coverage table with validation results
aspiratio-update

# Step 2: Download missing reports (auto-detects what's needed)
aspiratio-download

# Step 3: Validate downloaded PDFs
aspiratio-validate

# Step 4: Update coverage table
aspiratio-update

# Step 5: Retry failures with Playwright fallback
aspiratio-retry
```

---

## Test Connectivity

```bash
# Test all company URLs
aspiratio-diagnose

# Test specific URL
aspiratio-diagnose https://www.example.com/investors
```

---

## Interactive UI

```bash
streamlit run scripts/app.py
```

---

## Troubleshooting

### Issue: DNS Resolution Failures
```
🌐 DNS resolution failed - domain may be blocked or unreachable
```

**Solution:** Run in environment with internet access

### Issue: Coverage Table Out of Sync
**Symptom:** Coverage table shows fewer complete reports than validation_results.csv

**Solution:**
```bash
aspiratio-update
```

### Issue: Import Errors
**Solution:**
```bash
pip install -e .  # Reinstall with all dependencies
```

---

## Project Structure

```
aspiratio/
├── config.yaml                   # Configuration
├── coverage_table_updated.csv    # Progress tracking
├── validation_results.csv        # Validation status
├── instrument_master.csv         # Company database
├── scripts/
│   ├── download_reports.py       # Main downloader
│   ├── validate_reports.py       # Validator
│   └── app.py                    # Streamlit UI
└── aspiratio/
    ├── tier1/                    # Traditional scraping
    ├── tier2/                    # Playwright (JavaScript)
    └── tier3/                    # Manual recording
```

---

## Next Steps

1. **Fix connectivity** - Run in environment with internet
2. **Sync coverage** - Run `aspiratio-update`
3. **Download remaining** - Run `aspiratio-download`
4. **Handle edge cases** - Use Playwright for difficult sites

---

For detailed status, see [PROJECT_STATUS_SUMMARY.md](PROJECT_STATUS_SUMMARY.md)
