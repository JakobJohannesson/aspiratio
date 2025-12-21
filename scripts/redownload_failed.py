"""
Re-download reports for companies that failed validation.
Focuses on Atlas Copco, ABB, Boliden, and Epiroc with improved patterns.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aspiratio.utils.report_downloader import download_company_reports, download_pdf
from aspiratio.utils.playwright_downloader import find_reports_with_playwright
import pandas as pd

def redownload_atlas_copco():
    """
    Atlas Copco - Currently downloading quarterly reports instead of annual.
    Need to find the full annual reports (100+ pages).
    """
    print("\n" + "="*70)
    print("RE-DOWNLOADING: Atlas Copco (filtering quarterly reports)")
    print("="*70)
    
    # Try different IR URLs for Atlas Copco
    ir_urls = [
        "https://www.atlascopcogroup.com/en/investors/reports-and-presentations/annual-reports",
        "https://www.atlascopcogroup.com/en/investors/reports-and-presentations"
    ]
    
    for ir_url in ir_urls:
        print(f"\nTrying: {ir_url}")
        result = download_company_reports(
            cid='S6',
            company_name='Atlas Copco A',
            ir_url=ir_url,
            years=[2019, 2020, 2021, 2022, 2023, 2024],
            output_dir='companies'
        )
        
        # Check if we got any good downloads (>50 pages)
        if result:
            print(f"\nAtlas Copco result: {result}")
            break

def redownload_abb_with_playwright():
    """
    ABB - Use Playwright to get Group Annual Reports (not SEC filings).
    """
    print("\n" + "="*70)
    print("RE-DOWNLOADING: ABB with Playwright (Group Annual Reports)")
    print("="*70)
    
    ir_url = "https://global.abb/group/en/investors/annual-reporting-suite"
    years = [2019, 2020, 2021, 2022, 2023, 2024]
    
    # Use Playwright to find reports
    reports = find_reports_with_playwright(ir_url, years, "ABB")
    
    if not reports:
        print("  No reports found with Playwright, trying static search...")
        # Fallback to regular download
        result = download_company_reports(
            cid='S1',
            company_name='ABB Ltd',
            ir_url=ir_url,
            years=years,
            output_dir='companies'
        )
    else:
        # Download found reports
        company_dir = Path('companies') / 'S1'
        company_dir.mkdir(parents=True, exist_ok=True)
        
        downloaded = 0
        for report in reports:
            year = report['year']
            pdf_url = report['url']
            output_path = company_dir / f"annual_report_{year}.pdf"
            
            if output_path.exists():
                print(f"⊙ {year}: Already exists, skipping")
                continue
            
            print(f"Downloading {year}...")
            result = download_pdf(pdf_url, str(output_path), min_pages=50)
            
            if result['success']:
                print(f"✓ Downloaded: {result['pages']} pages, {result['size_mb']:.1f} MB")
                downloaded += 1
            else:
                print(f"✗ {year}: {result.get('error', 'Unknown error')}")
        
        print(f"\n✓ ABB: Downloaded {downloaded} new reports")

def redownload_boliden_epiroc():
    """
    Boliden and Epiroc - Some reports don't mention year in first 5 pages.
    Just re-download with same logic, validation will catch year issues.
    """
    companies = [
        {'cid': 'S7', 'name': 'Boliden', 'url': 'https://www.boliden.com/investors/reports-and-presentations/annual-and-sustainability-reports'},
        {'cid': 'S8', 'name': 'Epiroc A', 'url': 'https://www.epirocgroup.com/en/investors/reports-and-presentations/annual-reports'}
    ]
    
    for company in companies:
        print("\n" + "="*70)
        print(f"RE-DOWNLOADING: {company['name']} (potential year detection issues)")
        print("="*70)
        
        result = download_company_reports(
            cid=company['cid'],
            company_name=company['name'],
            ir_url=company['url'],
            years=[2019, 2020, 2021, 2022, 2023, 2024],
            output_dir='companies'
        )
        
        print(f"\n{company['name']} result: {result}")

def main():
    print("="*70)
    print("RE-DOWNLOAD FAILED VALIDATION COMPANIES")
    print("="*70)
    print("\nThis script re-downloads companies with validation issues:")
    print("  1. Atlas Copco - Quarterly reports instead of annual")
    print("  2. ABB - SEC filings instead of Group Annual Reports")
    print("  3. Boliden/Epiroc - Year detection issues")
    print("\n" + "="*70)
    
    # Load validation results to see what needs work
    try:
        df = pd.read_csv('validation_results.csv')
        
        # Show failed reports by company
        failed = df[df['Valid'] == False].groupby('Company_Name').size().sort_values(ascending=False)
        print("\nCompanies with failed validations:")
        for company, count in failed.items():
            print(f"  - {company}: {count} failed")
        print()
    except:
        pass
    
    # Ask user which to run
    print("\nSelect which companies to re-download:")
    print("  1. Atlas Copco (quarterly report issue)")
    print("  2. ABB (with Playwright for Group Annual Reports)")
    print("  3. Boliden & Epiroc (year detection issues)")
    print("  4. All of the above")
    print("  0. Exit")
    
    choice = input("\nEnter choice (0-4): ").strip()
    
    if choice == '1':
        redownload_atlas_copco()
    elif choice == '2':
        redownload_abb_with_playwright()
    elif choice == '3':
        redownload_boliden_epiroc()
    elif choice == '4':
        redownload_atlas_copco()
        redownload_abb_with_playwright()
        redownload_boliden_epiroc()
    else:
        print("Exiting...")
        return
    
    print("\n" + "="*70)
    print("RE-DOWNLOAD COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("  1. Run: python scripts/validate_reports.py")
    print("  2. Check validation_results.csv for improvements")
    print("  3. Review companies_validated/ folder for new reports")

if __name__ == '__main__':
    main()
