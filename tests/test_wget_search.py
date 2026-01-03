"""
Test wget-based search functionality.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aspiratio.tier1.wget_search import (
    normalize_company_name,
    find_reports_via_wget,
    get_company_mirror_dir
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


def test_mirror_directory():
    """Test mirror directory creation."""
    print("\n" + "="*80)
    print("Test: get_company_mirror_dir")
    print("="*80)
    
    test_cases = [
        ("S1", "mfn", "companies/S1/mirror_mfn"),
        ("S2", "cision", "companies/S2/mirror_cision"),
    ]
    
    for company_id, source, expected_path in test_cases:
        result = get_company_mirror_dir(company_id, source)
        status = "✓" if expected_path in str(result) else "✗"
        print(f"{status} {company_id}, {source:8} -> {result}")


def test_wget_integration():
    """Test wget integration (will check if wget is available)."""
    print("\n" + "="*80)
    print("Test: wget availability")
    print("="*80)
    
    import subprocess
    try:
        result = subprocess.run(['wget', '--version'], capture_output=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.decode('utf-8').split('\n')[0]
            print(f"✓ wget is available: {version}")
        else:
            print("✗ wget not working properly")
    except FileNotFoundError:
        print("✗ wget not found - install with: sudo apt-get install wget")
    except Exception as e:
        print(f"✗ Error checking wget: {e}")


if __name__ == "__main__":
    print("="*80)
    print("Wget Search Module Tests")
    print("="*80)
    
    test_normalize_company_name()
    test_mirror_directory()
    test_wget_integration()
    
    print("\n" + "="*80)
    print("Tests complete")
    print("="*80)
    print("\nNote: Full integration test requires network access and wget installed.")
    print("To test with real data, run: python aspiratio/tier1/wget_search.py")
