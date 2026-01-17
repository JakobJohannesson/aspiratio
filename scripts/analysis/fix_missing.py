#!/usr/bin/env python
"""
Fix script for companies that need special handling.

Based on failure analysis:
1. JavaScript-rendered pages → Use Playwright
2. HTTP 403 errors → Need different User-Agent or alternative URL
3. Partial coverage → Check subpages or Cision/MFN fallback
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Add project root to path
repo = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo))

from aspiratio.tier1.report_downloader import find_annual_reports
from aspiratio.tier1.mfn_search import search_mfn_reports
from aspiratio.tier2.playwright_downloader import PlaywrightDownloader

YEARS = [2019, 2020, 2021, 2022, 2023, 2024]

# Companies that need Playwright (JavaScript-rendered)
NEEDS_PLAYWRIGHT = [
    'S23',  # SEB A
    'S25',  # SKF B
    'S21',  # Sandvik
    'S18',  # NIBE Industrier B
]

# Companies with 403 errors (need alternative approach)
NEEDS_ALTERNATIVE_URL = [
    'S7',   # Boliden - use Cision/MFN
]

# Companies needing MFN/Cision fallback
NEEDS_MFN_FALLBACK = [
    'S26',  # Sv. Handelsbanken A
    'S29',  # Telia Company
]

# Direct IR URL fixes (wrong URL in coverage table)
URL_FIXES = {
    'S7': 'https://www.boliden.com/investor-relations',  # Boliden
}


def try_playwright_search(cid, company, ir_url, years):
    """Try finding reports using Playwright for JavaScript-rendered pages."""
    print(f"\n🎭 Playwright search for {company}...")
    
    try:
        with PlaywrightDownloader() as pw:
            reports = pw.find_annual_reports(ir_url, years)
            print(f"   Found {len(reports)} reports via Playwright")
            return reports
    except Exception as e:
        print(f"   Error: {e}")
        return []


def try_mfn_search(cid, company, years):
    """Try finding reports via MFN (Modular Finance News)."""
    print(f"\n📡 MFN search for {company}...")
    
    try:
        reports = search_mfn_reports(company, years)
        print(f"   Found {len(reports)} reports via MFN")
        return reports
    except Exception as e:
        print(f"   Error: {e}")
        return []


def fix_company(cid, company, ir_url, missing_years):
    """Attempt to fix a specific company."""
    print(f"\n{'='*60}")
    print(f"Fixing: {company} ({cid})")
    print(f"IR URL: {ir_url}")
    print(f"Missing years: {missing_years}")
    
    results = {
        'cid': cid,
        'company': company,
        'missing_years': missing_years,
        'found': [],
        'still_missing': [],
        'method': None,
    }
    
    # Apply URL fix if needed
    if cid in URL_FIXES:
        ir_url = URL_FIXES[cid]
        print(f"   Using fixed URL: {ir_url}")
    
    # Try different methods based on category
    found_reports = []
    
    if cid in NEEDS_PLAYWRIGHT:
        found_reports = try_playwright_search(cid, company, ir_url, missing_years)
        results['method'] = 'playwright'
        
    elif cid in NEEDS_ALTERNATIVE_URL or cid in NEEDS_MFN_FALLBACK:
        # Try MFN first
        found_reports = try_mfn_search(cid, company, missing_years)
        results['method'] = 'mfn'
        
        # If MFN fails, try standard search with fixed URL
        if not found_reports and cid in URL_FIXES:
            print("   MFN failed, trying standard search with fixed URL...")
            found_reports = find_annual_reports(ir_url, missing_years, max_depth=2)
            results['method'] = 'standard_fixed_url'
    else:
        # Standard approach
        found_reports = find_annual_reports(ir_url, missing_years, max_depth=2)
        results['method'] = 'standard'
    
    # Process results
    found_years = [r['year'] for r in found_reports]
    results['found'] = found_reports
    results['still_missing'] = [y for y in missing_years if y not in found_years]
    
    if found_reports:
        print(f"   ✓ Found: {sorted(found_years)}")
    if results['still_missing']:
        print(f"   ✗ Still missing: {results['still_missing']}")
    
    return results


def main():
    """Main fix routine."""
    print("Loading coverage data...")
    coverage = pd.read_csv(repo / 'coverage_table_updated.csv', sep='\t')
    validation = pd.read_csv(repo / 'validation_results.csv')
    
    # Get validated set
    validated_set = set(zip(validation['CID'], validation['Year']))
    
    # Get incomplete entries
    incomplete = coverage[coverage['Priority'] != 'Complete ✓'].copy()
    
    # Group by company
    companies_to_fix = {}
    for _, row in incomplete.iterrows():
        cid = row['Company_Identifier']
        if cid not in companies_to_fix:
            companies_to_fix[cid] = {
                'company': row['CompanyName'],
                'ir_url': row.get('IR_URL', ''),
                'missing_years': [],
            }
        companies_to_fix[cid]['missing_years'].append(int(row['FiscalYear']))
    
    print(f"\nFound {len(companies_to_fix)} companies to fix")
    
    # Fix each company
    all_results = []
    for cid, data in companies_to_fix.items():
        result = fix_company(
            cid, 
            data['company'], 
            data['ir_url'], 
            sorted(data['missing_years'])
        )
        all_results.append(result)
    
    # Summary
    print("\n" + "=" * 60)
    print("FIX SUMMARY")
    print("=" * 60)
    
    total_missing = sum(len(r['missing_years']) for r in all_results)
    total_found = sum(len(r['found']) for r in all_results)
    still_missing = sum(len(r['still_missing']) for r in all_results)
    
    print(f"Total missing before: {total_missing}")
    print(f"Found this run: {total_found}")
    print(f"Still missing: {still_missing}")
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = repo / 'agent_logs' / 'runs' / f'fix_results_{timestamp}.json'
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\nResults saved to: {output_path}")
    
    return all_results


if __name__ == '__main__':
    main()
