#!/usr/bin/env python3
"""
Analyze agent execution logs to identify patterns in failures and errors.
"""
import json
from pathlib import Path
from datetime import datetime
from collections import Counter
import pandas as pd


def load_latest_summary(logs_dir="agent_logs/runs"):
    """Load the most recent download summary."""
    logs_path = Path(logs_dir)
    summaries = sorted(logs_path.glob("download_summary_*.json"))
    
    if not summaries:
        print("No download summaries found!")
        return None
    
    latest = summaries[-1]
    with open(latest) as f:
        data = json.load(f)
    
    return latest, data


def analyze_errors(data):
    """Extract and categorize all errors from a download summary."""
    errors = []
    
    for company in data:
        if company['failed'] > 0:
            for download in company.get('downloads', []):
                if download['status'] == 'failed':
                    errors.append({
                        'company': company['company'],
                        'cid': company['cid'],
                        'year': download['year'],
                        'url': download.get('url', 'N/A'),
                        'error': download.get('error', 'Unknown error')
                    })
    
    return errors


def categorize_error(error_msg):
    """Categorize error messages into common patterns."""
    error_lower = error_msg.lower()
    
    if 'eof marker not found' in error_lower:
        return 'Invalid PDF (EOF marker missing)'
    elif 'page count' in error_lower or 'too few pages' in error_lower:
        return 'Page count out of range'
    elif 'company name not found' in error_lower:
        return 'Company name not detected'
    elif 'year not found' in error_lower or 'year detection' in error_lower:
        return 'Year not detected'
    elif 'timeout' in error_lower:
        return 'Download timeout'
    elif '404' in error_lower or 'not found' in error_lower:
        return 'URL not found (404)'
    elif 'connection' in error_lower or 'network' in error_lower:
        return 'Network error'
    else:
        return 'Other'


def print_error_analysis(summary_file, data):
    """Print comprehensive error analysis."""
    errors = analyze_errors(data)
    
    print("="*80)
    print(f"AGENT LOG ANALYSIS: {summary_file.name}")
    print(f"Timestamp: {summary_file.stem.split('_')[-2]}_{summary_file.stem.split('_')[-1]}")
    print("="*80)
    print()
    
    # Overall statistics
    total_companies = len(data)
    companies_with_failures = sum(1 for c in data if c.get('failed', 0) > 0)
    total_found = sum(c.get('found', 0) for c in data)
    total_downloaded = sum(c.get('downloaded', 0) for c in data)
    total_skipped = sum(c.get('skipped', 0) for c in data)
    total_failed = sum(c.get('failed', 0) for c in data)
    
    print("SUMMARY STATISTICS:")
    print(f"  Companies processed: {total_companies}")
    print(f"  Reports found: {total_found}")
    print(f"  Successfully downloaded: {total_downloaded}")
    print(f"  Skipped (already exists): {total_skipped}")
    print(f"  Failed: {total_failed}")
    print(f"  Companies with failures: {companies_with_failures}")
    print()
    
    if not errors:
        print("✓ No failures in this run!")
        return
    
    # Error categorization
    error_categories = Counter(categorize_error(e['error']) for e in errors)
    
    print("ERROR BREAKDOWN BY TYPE:")
    for category, count in error_categories.most_common():
        print(f"  {category}: {count}")
    print()
    
    # Group by company
    errors_by_company = {}
    for err in errors:
        company = err['company']
        if company not in errors_by_company:
            errors_by_company[company] = []
        errors_by_company[company].append(err)
    
    print("ERRORS BY COMPANY:")
    for company, company_errors in sorted(errors_by_company.items()):
        cid = company_errors[0]['cid']
        print(f"\n  {company} ({cid}) - {len(company_errors)} failures:")
        for err in company_errors:
            print(f"    • Year {err['year']}: {categorize_error(err['error'])}")
            print(f"      Error: {err['error']}")
            if err['url'] != 'N/A':
                print(f"      URL: {err['url']}")
    print()
    
    # Suggested fixes
    print("SUGGESTED FIXES:")
    for category, count in error_categories.most_common():
        if category == 'Invalid PDF (EOF marker missing)':
            print(f"  • {category} ({count} occurrences):")
            print("    - These URLs may be HTML pages or interactive reports, not PDFs")
            print("    - Check if there's a 'Download PDF' link on the page")
            print("    - May need to use Playwright for dynamic content")
        elif category == 'Page count out of range':
            print(f"  • {category} ({count} occurrences):")
            print("    - Verify these are full annual reports, not summaries")
            print("    - Check if quarterly reports were downloaded by mistake")
        elif category == 'Company name not detected':
            print(f"  • {category} ({count} occurrences):")
            print("    - Company name might use different spelling/format in PDF")
            print("    - Check alternative names in instrument_master.csv")
        elif category == 'Year not detected':
            print(f"  • {category} ({count} occurrences):")
            print("    - Year might be in different format (e.g., '2023/2024' for fiscal year)")
            print("    - Check if year appears later in document")
        elif category == 'URL not found (404)':
            print(f"  • {category} ({count} occurrences):")
            print("    - URLs may have changed on investor relations page")
            print("    - Update IR URLs in instrument_master.csv")


def main():
    """Main analysis function."""
    summary_file, data = load_latest_summary()
    
    if data is None:
        return
    
    print_error_analysis(summary_file, data)


if __name__ == "__main__":
    main()
