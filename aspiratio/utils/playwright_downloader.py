"""
Playwright-based downloader for JavaScript-heavy sites.
Handles companies where reports are loaded dynamically.
"""

from playwright.sync_api import sync_playwright
import re
import time
from urllib.parse import urljoin
from pathlib import Path

def find_reports_with_playwright(ir_url, years, company_name=""):
    """
    Use Playwright to load page and find annual report links.
    
    Args:
        ir_url: Investor relations URL
        years: List of years to find
        company_name: Company name for filtering
    
    Returns:
        List of dicts: [{'year': 2024, 'url': 'https://...', 'title': '...'}]
    """
    results = []
    
    print(f"  Using Playwright to load JavaScript content...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Set user agent
        page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        try:
            # Load page
            page.goto(ir_url, wait_until='domcontentloaded', timeout=20000)
            
            # Click any accordions/dropdowns to reveal content
            try:
                # Look for common accordion patterns
                accordion_selectors = [
                    'button[aria-expanded="false"]',
                    '.accordion-button',
                    '[data-toggle="collapse"]',
                    'summary',  # HTML details/summary
                ]
                
                for selector in accordion_selectors:
                    elements = page.query_selector_all(selector)
                    for element in elements[:10]:  # Limit to avoid timeout
                        try:
                            element.click()
                            page.wait_for_timeout(300)
                        except:
                            pass
            except:
                pass
            
            # Wait for dynamic content
            page.wait_for_timeout(2000)
            
            # Get page content
            content = page.content()
            
            # Extract PDF links from content using regex
            # Look for library.e.abb.com or other PDF links
            pdf_patterns = [
                r'https://library\.e\.abb\.com/[^"\s<>]+(?:Annual|annual)[^"\s<>]+(?:Report|report)[^"\s<>]+\.pdf[^"\s<>]*',
                r'https://[^"\s<>]+/[^"\s<>]*(?:annual|Annual)[^"\s<>]*(?:report|Report)[^"\s<>]*\.pdf[^"\s<>]*',
            ]
            
            found_urls = set()
            for pattern in pdf_patterns:
                matches = re.findall(pattern, content)
                found_urls.update(matches)
            
            print(f"  Found {len(found_urls)} potential PDF URLs in page content")
            
            # Try to match years
            for pdf_url in found_urls:
                # Clean URL (remove HTML entities, etc.)
                pdf_url = pdf_url.replace('&amp;', '&')
                
                # Extract year from URL
                year_match = re.search(r'20(19|20|21|22|23|24)', pdf_url)
                if year_match:
                    year = int(year_match.group(0))
                    if year in years:
                        # Extract filename for title
                        filename = pdf_url.split('/')[-1].split('?')[0]
                        
                        # Check if it looks like annual report (not quarterly)
                        if not re.search(r'q[1-4]|quarter|interim|delårs|kvartals', filename.lower()):
                            results.append({
                                'year': year,
                                'url': pdf_url,
                                'title': filename,
                                'source_page': ir_url
                            })
                            print(f"    ✓ Found {year}: {filename[:60]}")
            
            browser.close()
            
        except Exception as e:
            print(f"  ✗ Playwright error: {e}")
            browser.close()
            return []
    
    return results

def download_abb_reports(output_dir='companies'):
    """
    Special handler for ABB using Playwright.
    """
    from aspiratio.utils.report_downloader import download_pdf
    
    company_name = "ABB Ltd"
    cid = "S1"
    ir_url = "https://global.abb/group/en/investors/annual-reporting-suite"
    years = [2019, 2020, 2021, 2022, 2023, 2024]
    
    print(f"\n{'='*70}")
    print(f"Special Handler: {company_name} (Playwright)")
    print(f"{'='*70}\n")
    
    # Use Playwright to find reports
    reports = find_reports_with_playwright(ir_url, years, company_name)
    
    if not reports:
        print("  No reports found with Playwright")
        return
    
    # Create output directory
    company_dir = Path(output_dir) / cid
    company_dir.mkdir(parents=True, exist_ok=True)
    
    # Download each report
    downloaded = 0
    for report in reports:
        year = report['year']
        pdf_url = report['url']
        output_path = company_dir / f"annual_report_{year}.pdf"
        
        # Skip if exists
        if output_path.exists():
            print(f"⊙ {year}: Already exists, skipping")
            continue
        
        print(f"Downloading {year} from {pdf_url[:80]}...")
        result = download_pdf(pdf_url, str(output_path), min_pages=50)
        
        if result['success']:
            print(f"✓ Downloaded: {result['pages']} pages, {result['size_mb']:.1f} MB")
            downloaded += 1
        else:
            print(f"✗ {year}: {result.get('error', 'Unknown error')}")
    
    print(f"\n✓ ABB: Downloaded {downloaded} new reports")

if __name__ == '__main__':
    download_abb_reports()
