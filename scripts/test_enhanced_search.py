"""
Test script for enhanced IR page search with JSON extraction and failsafe.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aspiratio.utils.report_downloader import find_annual_reports

def test_company(company_name, ir_url):
    """Test the enhanced search for a single company."""
    print(f"\n{'='*80}")
    print(f"Testing: {company_name}")
    print(f"IR URL: {ir_url}")
    print(f"{'='*80}")
    
    try:
        reports = find_annual_reports(ir_url, years=[2024, 2023], max_depth=2, enable_failsafe=True)
        
        if reports:
            print(f"\n✓ SUCCESS: Found {len(reports)} reports")
            for report in reports:
                print(f"  - {report['year']}: {report['url'][:80]}")
        else:
            print(f"\n⚠ No reports found")
            
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Test with companies that had search failures
    test_cases = [
        ("NIBE", "https://www.nibe.com/en-eu/investors"),
        ("Volvo", "https://www.volvogroup.com/en/investors.html"),
    ]
    
    for company, url in test_cases:
        test_company(company, url)
    
    print(f"\n{'='*80}")
    print("Test complete")
    print(f"{'='*80}")
