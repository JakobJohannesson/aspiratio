#!/usr/bin/env python
"""
Diagnose why annual reports are failing to be found or downloaded.

This script analyzes the pipeline to identify:
1. Companies where IR page couldn't be found
2. Companies where candidates weren't found (no PDF links detected)
3. Companies where candidates were found but download failed
4. Companies where download succeeded but validation failed

It also attempts to diagnose the root cause and suggest fixes.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Add project root to path
repo = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo))

from aspiratio.tier1.report_downloader import find_annual_reports

# Configuration
YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
OUTPUT_DIR = repo / 'agent_logs' / 'runs'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_data():
    """Load all relevant data files."""
    coverage = pd.read_csv(repo / 'coverage_table_updated.csv', sep='\t')
    candidates = pd.read_csv(repo / 'report_candidates.csv')
    validation = pd.read_csv(repo / 'validation_results.csv')
    
    return coverage, candidates, validation


def categorize_failures(coverage, candidates, validation):
    """Categorize failures by root cause."""
    
    # Get validated company-years
    validated_set = set(zip(validation['CID'], validation['Year']))
    
    # Get candidate company-years  
    candidate_set = set(zip(candidates['Company_Identifier'], candidates['Year']))
    
    # Categorize each incomplete row
    incomplete = coverage[coverage['Priority'] != 'Complete ✓'].copy()
    
    categories = {
        'no_ir_url': [],           # No IR URL configured
        'ir_unreachable': [],      # IR URL doesn't respond
        'no_candidates': [],       # IR works but no PDF candidates found
        'download_failed': [],     # Candidates found but download failed
        'validation_failed': [],   # Download worked but validation failed
    }
    
    for _, row in incomplete.iterrows():
        cid = row['Company_Identifier']
        company = row['CompanyName']
        year = int(row['FiscalYear'])
        ir_url = row.get('IR_URL', '')
        
        entry = {
            'cid': cid,
            'company': company,
            'year': year,
            'ir_url': ir_url,
        }
        
        # Check if we have IR URL
        if not ir_url or pd.isna(ir_url):
            entry['reason'] = 'No IR URL configured'
            categories['no_ir_url'].append(entry)
            continue
        
        # Check if we found candidates for this company-year
        if (cid, year) not in candidate_set:
            entry['reason'] = 'No PDF candidates found for this year'
            categories['no_candidates'].append(entry)
            continue
        
        # We had candidates but not validated - check if download or validation failed
        # For now, categorize as download_failed (we can refine later)
        entry['reason'] = 'Candidates found but not validated'
        categories['download_failed'].append(entry)
    
    return categories


def diagnose_ir_page(ir_url, company, years):
    """Diagnose issues with an IR page."""
    diagnosis = {
        'url': ir_url,
        'company': company,
        'accessible': False,
        'status_code': None,
        'content_type': None,
        'has_pdf_links': False,
        'pdf_count': 0,
        'years_found': [],
        'issues': [],
        'suggestions': [],
    }
    
    try:
        resp = requests.get(ir_url, timeout=15, allow_redirects=True)
        diagnosis['status_code'] = resp.status_code
        diagnosis['content_type'] = resp.headers.get('Content-Type', '')
        diagnosis['final_url'] = resp.url
        
        if resp.status_code == 200:
            diagnosis['accessible'] = True
            
            # Check if it's HTML
            if 'html' in diagnosis['content_type'].lower():
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Count PDF links
                pdf_links = soup.find_all('a', href=re.compile(r'\.pdf', re.I))
                diagnosis['pdf_count'] = len(pdf_links)
                diagnosis['has_pdf_links'] = len(pdf_links) > 0
                
                # Check what years are mentioned
                text = soup.get_text()
                for year in years:
                    if str(year) in text:
                        diagnosis['years_found'].append(year)
                
                # Check for common issues
                if len(pdf_links) == 0:
                    diagnosis['issues'].append('No PDF links found on page')
                    
                    # Check if page uses JavaScript
                    scripts = soup.find_all('script')
                    if len(scripts) > 5:
                        diagnosis['issues'].append('Page appears to use heavy JavaScript (may need Playwright)')
                        diagnosis['suggestions'].append('Use Playwright tier for JavaScript-rendered content')
                    
                    # Check for iframes
                    iframes = soup.find_all('iframe')
                    if iframes:
                        diagnosis['issues'].append(f'Page contains {len(iframes)} iframe(s)')
                        diagnosis['suggestions'].append('Check iframe sources for PDF links')
                
                # Check if page redirects to login
                if 'login' in resp.url.lower() or 'sign' in resp.url.lower():
                    diagnosis['issues'].append('Page may require authentication')
                    
            else:
                diagnosis['issues'].append(f'Page is not HTML: {diagnosis["content_type"]}')
        else:
            diagnosis['issues'].append(f'HTTP {resp.status_code} error')
            
    except requests.exceptions.Timeout:
        diagnosis['issues'].append('Request timed out')
    except requests.exceptions.ConnectionError as e:
        diagnosis['issues'].append(f'Connection error: {str(e)[:50]}')
    except Exception as e:
        diagnosis['issues'].append(f'Error: {str(e)[:50]}')
    
    return diagnosis


def deep_diagnose_company(cid, company, ir_url, years):
    """Perform deep diagnosis for a specific company."""
    result = {
        'cid': cid,
        'company': company,
        'ir_url': ir_url,
        'ir_diagnosis': None,
        'search_results': None,
        'missing_years': [],
        'found_years': [],
        'root_cause': 'Unknown',
        'recommendations': [],
    }
    
    # Diagnose IR page
    result['ir_diagnosis'] = diagnose_ir_page(ir_url, company, years)
    
    # Try to find reports
    try:
        reports = find_annual_reports(ir_url, years, max_depth=2, verbose=False)
        result['search_results'] = {
            'count': len(reports),
            'years': [r['year'] for r in reports],
            'urls': [r['url'] for r in reports],
        }
        result['found_years'] = [r['year'] for r in reports]
        result['missing_years'] = [y for y in years if y not in result['found_years']]
    except Exception as e:
        result['search_results'] = {'error': str(e)}
        result['missing_years'] = years
    
    # Determine root cause
    ir_diag = result['ir_diagnosis']
    
    if not ir_diag['accessible']:
        result['root_cause'] = 'IR page not accessible'
        result['recommendations'].append('Check if URL is correct or if site is down')
    elif not ir_diag['has_pdf_links']:
        if 'JavaScript' in str(ir_diag['issues']):
            result['root_cause'] = 'JavaScript-rendered page'
            result['recommendations'].append('Use Playwright-based scraping')
        else:
            result['root_cause'] = 'No PDF links on page'
            result['recommendations'].append('Check if reports are behind navigation/subpages')
            result['recommendations'].append('Look for alternative IR page URL')
    elif result['missing_years']:
        result['root_cause'] = f'Partial coverage ({len(result["found_years"])}/{len(years)} years)'
        result['recommendations'].append('Some years may be archived or on different pages')
        result['recommendations'].append('Check for pattern in found years vs missing years')
    else:
        result['root_cause'] = 'Unknown - needs manual investigation'
    
    return result


def analyze_company_patterns(coverage, candidates):
    """Analyze patterns across companies to find common issues."""
    patterns = {
        'domains': {},
        'url_patterns': {},
        'success_by_domain': {},
    }
    
    # Group by domain
    for _, row in coverage.iterrows():
        ir_url = row.get('IR_URL', '')
        if not ir_url or pd.isna(ir_url):
            continue
        
        domain = urlparse(ir_url).netloc
        if domain not in patterns['domains']:
            patterns['domains'][domain] = {'companies': [], 'complete': 0, 'incomplete': 0}
        
        patterns['domains'][domain]['companies'].append(row['CompanyName'])
        if row['Priority'] == 'Complete ✓':
            patterns['domains'][domain]['complete'] += 1
        else:
            patterns['domains'][domain]['incomplete'] += 1
    
    return patterns


def generate_report(categories, company_diagnoses, patterns):
    """Generate a comprehensive failure analysis report."""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = OUTPUT_DIR / f'failure_analysis_{timestamp}.json'
    
    report = {
        'timestamp': timestamp,
        'summary': {
            'total_incomplete': sum(len(v) for v in categories.values()),
            'by_category': {k: len(v) for k, v in categories.items()},
        },
        'categories': categories,
        'company_diagnoses': company_diagnoses,
        'patterns': patterns,
        'priority_fixes': [],
    }
    
    # Identify priority fixes (companies with most missing years)
    company_missing = {}
    for cat, entries in categories.items():
        for entry in entries:
            company = entry['company']
            if company not in company_missing:
                company_missing[company] = {'count': 0, 'years': [], 'category': cat}
            company_missing[company]['count'] += 1
            company_missing[company]['years'].append(entry['year'])
    
    # Sort by most missing
    priority = sorted(company_missing.items(), key=lambda x: -x[1]['count'])
    report['priority_fixes'] = [
        {
            'company': company,
            'missing_years': data['years'],
            'primary_category': data['category'],
        }
        for company, data in priority[:10]
    ]
    
    # Save report
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    return report, report_path


def print_summary(report):
    """Print a human-readable summary."""
    print("\n" + "=" * 70)
    print("FAILURE ANALYSIS REPORT")
    print("=" * 70)
    
    print(f"\n📊 Summary:")
    print(f"   Total incomplete: {report['summary']['total_incomplete']} company-years")
    print(f"\n   By category:")
    for cat, count in report['summary']['by_category'].items():
        if count > 0:
            print(f"   • {cat}: {count}")
    
    print(f"\n🎯 Priority Fixes (companies with most missing years):")
    for i, fix in enumerate(report['priority_fixes'], 1):
        years = sorted(fix['missing_years'])
        years_str = ', '.join(map(str, years))
        print(f"   {i}. {fix['company']}: {len(fix['missing_years'])} years ({years_str})")
        print(f"      Category: {fix['primary_category']}")
    
    print("\n" + "=" * 70)


def main():
    """Main analysis function."""
    print("Loading data...")
    coverage, candidates, validation = load_data()
    
    print("Categorizing failures...")
    categories = categorize_failures(coverage, candidates, validation)
    
    print("Analyzing patterns...")
    patterns = analyze_company_patterns(coverage, candidates)
    
    # Deep diagnose worst offenders
    print("\nPerforming deep diagnosis on problem companies...")
    company_diagnoses = {}
    
    # Get unique companies with issues
    problem_companies = set()
    for cat, entries in categories.items():
        for entry in entries:
            problem_companies.add((entry['cid'], entry['company'], entry['ir_url']))
    
    for cid, company, ir_url in list(problem_companies)[:10]:  # Limit to top 10
        print(f"  Diagnosing: {company}...")
        if ir_url and not pd.isna(ir_url):
            diagnosis = deep_diagnose_company(cid, company, ir_url, YEARS)
            company_diagnoses[cid] = diagnosis
    
    print("\nGenerating report...")
    report, report_path = generate_report(categories, company_diagnoses, patterns)
    
    print_summary(report)
    
    print(f"\n📄 Full report saved to: {report_path}")
    
    return report


if __name__ == '__main__':
    main()
