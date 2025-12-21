# Enhanced IR Page Search - Implementation Summary

## Date: 2025-12-21

## Overview
Implemented a comprehensive enhancement to the annual report search functionality in `report_downloader.py` to improve discovery success rates through multiple strategies.

## Key Enhancements

### 1. JSON-Based Link Extraction (`extract_links_from_page`)
**Purpose**: Extract all available links from IR pages, including those hidden in JavaScript/JSON structures.

**Features**:
- **HTML links**: Standard `<a>` tags
- **JSON-LD structured data**: Parses `application/ld+json` scripts common on modern IR pages
- **Navigation menus**: Prioritizes links from `<nav>`, `<header>`, and navigation classes
- **Footer sections**: Extracts investor relations links from page footers
- **Data attributes**: Captures links from `data-href`, `data-url` attributes used in JavaScript

**Result**: Typically extracts 1000-2000+ links per page (vs ~200 before)

### 2. Link Prioritization Strategy
**Navigation/Footer Links**: Given priority in the search queue as they're more likely to contain correct annual reports sections

**Implementation**:
```python
if is_priority_link:
    pages_to_visit.insert(0, abs_url)  # Front of queue
else:
    pages_to_visit.append(abs_url)  # Normal queue
```

### 3. Failsafe Mechanism (`find_ir_page_from_main_site`)
**Trigger**: Activates when no reports found after standard search + common patterns

**Strategy**:
1. Navigate to main company website (root domain)
2. Search footer for investor relations links
3. Search navigation for investor relations links  
4. Try common IR path patterns (`/investors`, `/investor-relations`, etc.)
5. Retry search from newly discovered IR page

**Benefits**:
- Handles outdated IR URLs in instrument_master.csv
- Discovers correct IR pages even when provided URL has moved
- Single recursive call (failsafe=False on retry) prevents infinite loops

### 4. Improved Error Handling
**Problem**: Consecutive 404s from common pattern attempts were terminating searches prematurely

**Solution**: Reset failure counter when trying alternative patterns
```python
except DownloadError:
    consecutive_failures = 0  # Don't let pattern 404s stop failsafe
    continue
```

## Test Results

### NIBE Test
- Initial IR URL: `https://www.nibe.com/en-eu/investors` (404)
- Failsafe discovered: `https://www.nibe.com/investors/nibe-share` (footer link)
- Link extraction: 1984-2235 links per page
- Result: System now reaches correct IR section (though reports still not found due to site structure)

### Volvo Test  
- Initial IR URL: `https://www.volvogroup.com/en/investors.html` (no reports)
- Failsafe discovered: `https://www.volvogroup.com/en/investors/reports-and-presentations.html` (footer)
- Link extraction: 1125-1135 links per page
- Result: Correctly navigates to reports section

## Code Structure

### New Functions
1. **`extract_links_from_page(url, soup)`**
   - Returns: List of dicts with href, text, title, source
   - Sources: html, json-ld, navigation, footer, data-attr

2. **`find_ir_page_from_main_site(main_url)`**
   - Returns: IR URL if found, else None
   - Searches: footer → navigation → common patterns

### Modified Functions
3. **`find_annual_reports(..., enable_failsafe=True)`**
   - Added: `enable_failsafe` parameter (default True)
   - Enhanced: Uses `extract_links_from_page` instead of simple `find_all('a')`
   - Added: Failsafe logic at end before returning results

## Impact on Success Rate

**Before**: 7.2% success rate (6/83 reports)
- Many failures due to HTTP 404 on outdated IR URLs
- Limited link extraction missed reports in navigation/JSON

**Expected After**:
- Improved discovery of correct IR pages via failsafe
- Better report detection via comprehensive link extraction
- Reduced false "not found" due to missing navigation links

## Usage

### Default (with failsafe)
```python
reports = find_annual_reports(ir_url, years=[2019, 2024])
```

### Disable failsafe (for recursive calls)
```python
reports = find_annual_reports(ir_url, years=[2019, 2024], enable_failsafe=False)
```

## Next Steps

1. **Test on full dataset**: Run `redownload_failed.py` again to measure improvement
2. **Monitor failsafe usage**: Track how often failsafe discovers correct IR pages
3. **Add caching**: Consider caching discovered IR URLs to avoid repeated failsafe searches
4. **Expand patterns**: Add more company-specific patterns based on failure analysis

## Files Modified
- `aspiratio/utils/report_downloader.py` (main implementation)
- `scripts/test_enhanced_search.py` (test script)

## Transparency
The enhanced search now shows:
- Total links found: "Found 1125 links to analyze (from HTML, JSON, nav, footer)"
- Failsafe activation: "⚠ No reports found, activating failsafe..."
- IR discovery: "✓ Found IR link in footer: financial reports"
- Retry attempt: "→ Retrying search from discovered IR page: ..."
