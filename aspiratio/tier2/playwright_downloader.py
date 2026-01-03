"""
Playwright-based downloader for JavaScript-heavy sites.
Handles companies where reports are loaded dynamically.
"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import re
import time
from urllib.parse import urljoin
from pathlib import Path
import asyncio
from playwright.async_api import async_playwright

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
    from aspiratio.tier1.report_downloader import download_pdf
    
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

async def download_atlas_copco_report(year, output_dir='companies'):
    """
    Download Atlas Copco annual report for specific year using recorded navigation.
    Based on playwright script generated from codegen.
    
    Args:
        year: Year to download (e.g., 2024)
        output_dir: Output directory (default: 'companies')
    
    Returns:
        dict: {'success': bool, 'url': str, 'path': str, 'error': str}
    """
    from aspiratio.tier1.report_downloader import download_pdf
    
    company_name = "Atlas Copco AB"
    cid = "S6"
    ir_url = "https://www.atlascopcogroup.com/en/investors"
    
    # Create output directory
    company_dir = Path(output_dir) / cid
    company_dir.mkdir(parents=True, exist_ok=True)
    output_path = company_dir / f"annual_report_{year}.pdf"
    
    # Skip if exists (simple check by file size)
    if output_path.exists() and output_path.stat().st_size > 1_000_000:  # > 1MB
        return {
            'success': True,
            'url': None,
            'path': str(output_path),
            'error': 'Already exists'
        }
    
    print(f"\n{'='*70}")
    print(f"Atlas Copco AB ({cid}) - {year} (Playwright)")
    print(f"{'='*70}\n")
    
    pdf_url = None
    
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            print(f"  Loading {ir_url}...")
            await page.goto(ir_url, timeout=20000)
            
            # Handle cookie consent if present
            try:
                await page.locator(".onetrust-pc-dark-filter").click(timeout=3000)
                await page.get_by_role("button", name="Allow only necessary").click(timeout=3000)
                print("  ✓ Cookie consent handled")
            except PlaywrightTimeout:
                print("  ⊙ No cookie consent popup")
            except Exception as e:
                print(f"  ⊙ Cookie consent handling: {e}")
            
            # Navigate to Reports and presentations
            try:
                await page.get_by_role("link", name="Reports and presentations Download our financial documents").click(timeout=5000)
                print("  ✓ Navigated to Reports section")
                await page.wait_for_timeout(1000)
            except Exception as e:
                print(f"  ✗ Failed to navigate to Reports section: {e}")
                await browser.close()
                return {
                    'success': False,
                    'url': None,
                    'path': None,
                    'error': f'Navigation failed: {e}'
                }
            
            # Find the annual report link for the specific year
            # Try two different navigation patterns based on year
            try:
                # Pattern 1: Direct link (works for 2024)
                link_text = f"Annual Report {year} (PDF)"
                print(f"  Looking for: {link_text}")
                
                try:
                    link = page.get_by_role("link", name=link_text)
                    
                    # Extract href before clicking
                    pdf_url = await link.get_attribute('href', timeout=3000)
                    if pdf_url:
                        # Make absolute URL if relative
                        if not pdf_url.startswith('http'):
                            pdf_url = urljoin(ir_url, pdf_url)
                        print(f"  ✓ Found report URL (direct link): {pdf_url}")
                    else:
                        # Try clicking and capturing popup if no direct href
                        async with page.expect_popup(timeout=5000) as popup_info:
                            await link.click()
                        popup = await popup_info.value
                        pdf_url = popup.url
                        print(f"  ✓ Found report URL (via popup): {pdf_url}")
                        await popup.close()
                except:
                    # Pattern 2: Tab navigation (works for 2023 and earlier)
                    print(f"  ⊙ Direct link not found, trying tab navigation...")
                    
                    # Click year tab
                    await page.get_by_role("tab", name=str(year)).click(timeout=5000)
                    print(f"  ✓ Clicked {year} tab")
                    await page.wait_for_timeout(1000)
                    
                    # Click Annual Report button (this expands the section)
                    await page.get_by_role("button", name="Annual Report").click(timeout=5000)
                    print(f"  ✓ Clicked Annual Report button")
                    await page.wait_for_timeout(1000)
                    
                    # Click the link to go to the press release page
                    # This link typically says something like "Atlas Copco Group publishes"
                    publish_link = page.get_by_role("link").filter(has_text=re.compile("publishes", re.IGNORECASE)).first
                    await publish_link.click(timeout=5000)
                    print(f"  ✓ Navigated to press release page")
                    await page.wait_for_timeout(2000)  # Give page time to load
                    
                    # Now on the press release page, look for the actual annual report PDF link
                    # This is different from the press release PDF - look for link with year reference
                    # The pattern from recording: "20240321 Annual report incl."
                    # More generally: date + "annual report" + "incl" (for "including sustainability")
                    links = page.locator('a')
                    
                    # Try multiple patterns
                    try:
                        # Pattern 1: Date + "Annual report incl"
                        pdf_link = links.filter(has_text=re.compile(r"\d{8}.*[Aa]nnual.*[Rr]eport.*incl", re.IGNORECASE)).first
                        link_text = await pdf_link.text_content()
                        print(f"  → Found link: {link_text.strip()}")
                    except:
                        # Pattern 2: Just look for PDF links in the content area
                        pdf_link = links.filter(has=page.locator('text=/\\.pdf/i')).first
                    
                    # Get the href
                    pdf_url = await pdf_link.get_attribute('href', timeout=5000)
                    
                    if pdf_url:
                        # Make absolute URL if relative
                        if not pdf_url.startswith('http'):
                            pdf_url = urljoin(ir_url, pdf_url)
                        print(f"  ✓ Found report URL (tab navigation): {pdf_url}")
                
            except Exception as e:
                print(f"  ✗ Failed to find report: {e}")
                await browser.close()
                return {
                    'success': False,
                    'url': None,
                    'path': None,
                    'error': f'Report link not found: {e}'
                }
            
            await browser.close()
            
        except Exception as e:
            print(f"  ✗ Playwright error: {e}")
            return {
                'success': False,
                'url': None,
                'path': None,
                'error': str(e)
            }
    
    # Download the PDF
    if pdf_url:
        print(f"\n  Downloading from {pdf_url[:80]}...")
        result = download_pdf(pdf_url, str(output_path), min_pages=50)
        
        if result['success']:
            print(f"  ✓ Downloaded: {result['pages']} pages, {result['size_mb']:.1f} MB")
            return {
                'success': True,
                'url': pdf_url,
                'path': str(output_path),
                'error': None
            }
        else:
            print(f"  ✗ Download failed: {result.get('error', 'Unknown error')}")
            return {
                'success': False,
                'url': pdf_url,
                'path': None,
                'error': result.get('error', 'Download failed')
            }
    
    return {
        'success': False,
        'url': None,
        'path': None,
        'error': 'No PDF URL found'
    }

def download_atlas_copco_reports(years=[2019, 2020, 2021, 2022, 2023, 2024], output_dir='companies'):
    """
    Download Atlas Copco annual reports for multiple years.
    
    Args:
        years: List of years to download
        output_dir: Output directory
    
    Returns:
        List of results for each year
    """
    results = []
    
    for year in years:
        result = asyncio.run(download_atlas_copco_report(year, output_dir))
        results.append({
            'year': year,
            **result
        })
        time.sleep(1)  # Be nice to the server
    
    # Summary
    successful = sum(1 for r in results if r['success'])
    print(f"\n{'='*70}")
    print(f"✓ Atlas Copco: {successful}/{len(years)} reports downloaded successfully")
    print(f"{'='*70}\n")
    
    return results

if __name__ == '__main__':
    # Test Atlas Copco downloader
    print("Testing Atlas Copco downloader...")
    download_atlas_copco_reports(years=[2024])
    
    # Uncomment to test ABB
    # download_abb_reports()


# Registry of company-specific Playwright handlers
PLAYWRIGHT_HANDLERS = {
    'S6': download_atlas_copco_report,  # Atlas Copco AB
    # Add more as they're recorded:
    # 'S14': download_nibe_report,
    # 'S21': download_saab_report,
    # etc.
}
