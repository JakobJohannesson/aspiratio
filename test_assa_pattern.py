"""Test ASSA ABLOY URL pattern discovery."""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

def test_assa_abloy_pattern():
    base_url = "https://www.assaabloy.com/group/en/investors/reports-presentations/annual-reports"
    
    print(f"Testing ASSA ABLOY URL pattern discovery")
    print(f"{'='*70}\n")
    
    # Test 1: Check main page for year links
    print("Test 1: Checking main page for links to year-specific pages...")
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    resp = requests.get(base_url, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}\n")
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Look for links containing years 2019-2024
    all_links = soup.find_all('a', href=True)
    print(f"Total links found: {len(all_links)}\n")
    
    year_links = []
    for link in all_links:
        href = link.get('href', '')
        text = link.get_text(strip=True)
        
        # Check if link contains a year (2019-2024)
        if re.search(r'202[0-4]|2019', href) or re.search(r'202[0-4]|2019', text):
            abs_url = urljoin(base_url, href)
            year_links.append({
                'url': abs_url,
                'text': text,
                'href': href
            })
    
    print(f"Links with years 2019-2024: {len(year_links)}")
    if year_links:
        print("\nFound year links:")
        for link in year_links[:10]:  # Show first 10
            print(f"  - {link['text'][:50]} -> {link['url']}")
    else:
        print("  None found in HTML (likely JavaScript-rendered)")
    
    # Test 2: Try constructing year-specific URLs directly
    print(f"\n{'='*70}")
    print("Test 2: Testing if year-specific pages exist by construction...")
    years = [2019, 2020, 2021, 2022, 2023, 2024]
    
    for year in years:
        year_url = f"{base_url}/{year}"
        resp = requests.get(year_url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            pdf_links = [a for a in soup.find_all('a', href=True) if '.pdf' in a.get('href', '').lower()]
            print(f"  {year}: ✓ Page exists, found {len(pdf_links)} PDF links")
            
            # Show the PDF links
            for link in pdf_links[:3]:  # First 3
                pdf_url = urljoin(year_url, link.get('href'))
                print(f"    - {pdf_url}")
        else:
            print(f"  {year}: ✗ HTTP {resp.status_code}")
    
    # Test 3: Try the direct PDF URL pattern
    print(f"\n{'='*70}")
    print("Test 3: Testing direct PDF URL patterns (both capitalizations)...")
    patterns = [
        ("Capital R", "https://www.assaabloy.com/group/en/documents/investors/annual-reports/{year}/Annual%20Report%20{year}.pdf"),
        ("Lowercase r", "https://www.assaabloy.com/group/en/documents/investors/annual-reports/{year}/Annual%20report%20{year}.pdf"),
    ]
    
    for year in years:
        found = False
        for pattern_name, pattern in patterns:
            pdf_url = pattern.format(year=year)
            resp = requests.head(pdf_url, headers=headers, timeout=10, allow_redirects=True)
            
            if resp.status_code == 200:
                print(f"  {year}: ✓ PDF exists ({pattern_name})")
                found = True
                break
        
        if not found:
            print(f"  {year}: ✗ Not found")

if __name__ == "__main__":
    test_assa_abloy_pattern()
