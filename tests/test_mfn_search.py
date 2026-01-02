"""
Test MFN search functionality with real-world examples.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aspiratio.tier1.mfn_search import (
    normalize_company_name,
    find_mfn_company_page,
    search_mfn_for_report,
    extract_cision_attachments,
    find_reports_via_mfn
)

def test_normalize_company_name():
    """Test company name normalization."""
    print("\n" + "="*80)
    print("Test: normalize_company_name")
    print("="*80)
    
    test_cases = [
        ("Hexagon AB", "hexagon"),
        ("ASSA ABLOY AB", "assa"),
        ("Atlas Copco A", "atlas"),
        ("ABB Ltd", "abb"),
    ]
    
    for input_name, expected in test_cases:
        result = normalize_company_name(input_name)
        status = "✓" if result == expected else "✗"
        print(f"{status} {input_name:25} -> {result:15} (expected: {expected})")

def test_find_mfn_company_page():
    """Test finding MFN company pages."""
    print("\n" + "="*80)
    print("Test: find_mfn_company_page")
    print("="*80)
    
    test_cases = [
        "Hexagon AB",
        "ASSA ABLOY AB",
        "Atlas Copco A",
    ]
    
    for company in test_cases:
        print(f"\nTesting: {company}")
        result = find_mfn_company_page(company)
        if result:
            print(f"  ✓ Found: {result}")
        else:
            print(f"  ✗ Not found")

def test_full_mfn_search():
    """Test full MFN search workflow."""
    print("\n" + "="*80)
    print("Test: find_reports_via_mfn (Full workflow)")
    print("="*80)
    
    # Test with Hexagon for 2020 (as per problem statement)
    company = "Hexagon AB"
    years = [2020]
    
    print(f"\nSearching for {company} annual reports for years: {years}")
    results = find_reports_via_mfn(company, years)
    
    if results:
        print(f"\n✓ SUCCESS: Found {len(results)} reports")
        for r in results:
            print(f"  Year: {r['year']}")
            print(f"  Title: {r['title']}")
            print(f"  URL: {r['url']}")
            print(f"  Source: {r['source_page']}")
            print()
    else:
        print("\n✗ No reports found")

if __name__ == "__main__":
    print("="*80)
    print("MFN Search Module Tests")
    print("="*80)
    
    # Run tests
    test_normalize_company_name()
    
    # These tests require network access to mfn.se
    # They may fail in restricted environments
    try:
        test_find_mfn_company_page()
        test_full_mfn_search()
    except Exception as e:
        print(f"\n⚠ Network tests failed (may be expected in restricted environment): {e}")
    
    print("\n" + "="*80)
    print("Tests complete")
    print("="*80)
