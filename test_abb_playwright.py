"""Test ABB with Playwright to get JavaScript-rendered links."""
from playwright.sync_api import sync_playwright
import re

url = 'https://global.abb/group/en/investors/annual-reporting-suite'

print("Loading ABB page with Playwright...\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # Set timeout
    page.set_default_timeout(10000)
    
    try:
        page.goto(url, wait_until='domcontentloaded', timeout=15000)
        
        # Wait a bit for JavaScript
        page.wait_for_timeout(2000)
        
        # Get page HTML content
        content = page.content()
        
        print(f"Page loaded, HTML size: {len(content)} bytes\n")
        
        # Check if library.e.abb.com appears in the raw HTML
        if 'library.e.abb.com' in content:
            print("✓ Found library.e.abb.com references in HTML")
            
            # Use regex to extract all library.e.abb.com URLs
            library_urls = re.findall(r'https://library\.e\.abb\.com/[^"\s<>]+\.pdf[^"\s<>]*', content)
            
            print(f"Found {len(library_urls)} library.e.abb.com PDF URLs:\n")
            
            for pdf_url in library_urls[:15]:
                year_match = re.search(r'20(19|20|21|22|23|24)', pdf_url)
                year = year_match.group(0) if year_match else '????'
                
                # Extract filename
                filename = pdf_url.split('/')[-1].split('?')[0]
                
                print(f"{year}: {filename[:70]}")
                print(f"     {pdf_url[:120]}")
                print()
        else:
            print("✗ No library.e.abb.com references found in HTML")
            print("  Content might be loaded via additional XHR requests")
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        browser.close()
