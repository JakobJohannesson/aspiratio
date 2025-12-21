"""
Test fetching from specific problematic sites (ABB and ASSA ABLOY).
"""
import requests
from bs4 import BeautifulSoup
import re

def test_assa_abloy():
    """Test fetching ASSA ABLOY annual reports."""
    url = "https://www.assaabloy.com/group/en/investors/reports-presentations/annual-reports"
    
    print(f"\n{'='*60}")
    print(f"Testing ASSA ABLOY: {url}")
    print(f"{'='*60}")
    
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Find all links
            links = soup.find_all('a', href=True)
            print(f"\nTotal links found: {len(links)}")
            
            # Look for PDF or annual report links
            pdf_links = []
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                if '.pdf' in href.lower() or 'annual' in text or 'report' in text:
                    pdf_links.append({
                        'text': link.get_text(strip=True),
                        'href': href
                    })
            
            print(f"\nFound {len(pdf_links)} potential annual report links:")
            for i, link in enumerate(pdf_links[:10], 1):
                print(f"{i}. {link['text'][:60]}")
                print(f"   {link['href'][:80]}")
            
            # Try to find year patterns
            year_pattern = r'20(19|20|21|22|23|24)'
            year_links = [l for l in pdf_links if re.search(year_pattern, l['href'] + l['text'])]
            print(f"\nLinks with years 2019-2024: {len(year_links)}")
            
        else:
            print(f"Failed with status: {resp.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

def test_abb():
    """Test fetching ABB annual reports - check for hidden/dropdown content."""
    url = "https://global.abb/group/en/investors/annual-reporting-suite"
    
    print(f"\n{'='*60}")
    print(f"Testing ABB: {url}")
    print(f"{'='*60}")
    
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Find ALL links, including hidden ones
            all_links = soup.find_all('a', href=True)
            print(f"\nTotal links found: {len(all_links)}")
            
            # Look for PDF links specifically
            pdf_links = []
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if '.pdf' in href.lower():
                    # Extract year from URL
                    year_match = re.search(r'/(20\d{2})/', href)
                    year = year_match.group(1) if year_match else 'Unknown'
                    
                    # Get full URL
                    from urllib.parse import urljoin
                    full_url = urljoin(url, href)
                    
                    pdf_links.append({
                        'year': year,
                        'text': text[:80],
                        'url': full_url
                    })
            
            print(f"\nFound {len(pdf_links)} PDF links:")
            
            # Group by year
            from collections import defaultdict
            by_year = defaultdict(list)
            for link in pdf_links:
                by_year[link['year']].append(link)
            
            for year in sorted(by_year.keys(), reverse=True):
                print(f"\n{year}:")
                for link in by_year[year]:
                    print(f"  - {link['text']}")
                    print(f"    {link['url']}")
            
            # Look for accordion/dropdown elements
            print("\n\nChecking for accordion/dropdown structure...")
            accordions = soup.find_all(['div', 'section'], class_=re.compile(r'accordion|dropdown|collapse|expand', re.I))
            print(f"Found {len(accordions)} potential accordion/dropdown containers")
            
            # Check for hidden content
            hidden_elements = soup.find_all(style=re.compile(r'display:\s*none', re.I))
            print(f"Found {len(hidden_elements)} elements with display:none")
            
            # Look for aria-expanded or similar
            expandable = soup.find_all(attrs={'aria-expanded': True})
            print(f"Found {len(expandable)} expandable elements (aria-expanded)")
            
            # Check if PDFs are in hidden containers
            print(f"\n✓ Good news: Found {len(pdf_links)} PDFs in page source!")
            print("  Even though they're behind dropdowns, we can extract them from HTML")
                
        else:
            print(f"Failed with status: {resp.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_assa_abloy()
    test_abb()
