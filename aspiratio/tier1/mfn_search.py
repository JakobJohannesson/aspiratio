"""
MFN.se search source for annual reports.

This module provides functionality to search for annual reports on mfn.se,
a Swedish financial news site that aggregates company reports and press releases.

Example flow for Hexagon:
1. Find company page: https://mfn.se/all/a/hexagon
2. Search for reports: https://mfn.se/all/a/hexagon?query=2020%20annual%20report
3. Extract report links: https://mfn.se/cis/a/hexagon/hexagon-publishes-the-annual-report-and-sustainability-report-2020-0b9b3bd0
4. Find Cision attachments: https://mb.cision.com/Main/387/3318474/1396045.pdf
"""
import re
import requests
from urllib.parse import urljoin, urlparse, quote
from bs4 import BeautifulSoup
import time


def get_random_user_agent():
    """Return a user agent string."""
    return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def normalize_company_name(company_name):
    """
    Normalize company name for MFN search.
    
    Args:
        company_name: Company name (e.g., "Hexagon AB")
    
    Returns:
        Normalized name for URL (e.g., "hexagon")
    """
    # Remove common suffixes
    name = re.sub(r'\s+(ab|ltd|corp|inc|group|abp|as|asa|sa|nv|plc)$', '', company_name, flags=re.IGNORECASE)
    # Remove special characters and convert to lowercase
    name = re.sub(r'[^a-z0-9\s]', '', name.lower())
    # Take first word (usually the main company name)
    name = name.strip().split()[0] if name.strip() else company_name.lower()
    return name


def find_mfn_company_page(company_name):
    """
    Find the MFN page for a company.
    
    Args:
        company_name: Company name to search for
    
    Returns:
        MFN URL if found, None otherwise
    """
    normalized_name = normalize_company_name(company_name)
    
    # Try direct URL pattern first (most common)
    # Pattern: https://mfn.se/all/a/{company_name}
    test_url = f"https://mfn.se/all/a/{normalized_name}"
    
    try:
        print(f"  🔍 Trying MFN direct URL: {test_url}")
        headers = {"User-Agent": get_random_user_agent()}
        resp = requests.get(test_url, headers=headers, timeout=15, allow_redirects=True)
        
        if resp.status_code == 200:
            # Verify this is a company page (not a 404 soft page)
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Check for company indicators
            if soup.find('h1') or soup.find(class_=re.compile(r'company|ticker', re.I)):
                print(f"    ✓ Found MFN company page")
                return test_url
    except Exception as e:
        print(f"    ✗ Error checking direct URL: {e}")
    
    # Try alternative patterns (some companies use different naming)
    # Pattern: https://mfn.se/all/{company_name}
    alternative_url = f"https://mfn.se/all/{normalized_name}"
    try:
        print(f"  🔍 Trying MFN alternative URL: {alternative_url}")
        headers = {"User-Agent": get_random_user_agent()}
        resp = requests.get(alternative_url, headers=headers, timeout=15, allow_redirects=True)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            if soup.find('h1') or soup.find(class_=re.compile(r'company|ticker', re.I)):
                print(f"    ✓ Found MFN company page (alternative)")
                return alternative_url
    except Exception as e:
        print(f"    ✗ Error checking alternative URL: {e}")
    
    print(f"    ✗ Could not find MFN page for {company_name}")
    return None


def search_mfn_for_report(company_page_url, year):
    """
    Search MFN company page for annual report for a specific year.
    
    Args:
        company_page_url: MFN company page URL
        year: Year to search for (e.g., 2020)
    
    Returns:
        List of report page URLs found
    """
    try:
        # Build search query
        search_query = f"{year} annual report"
        search_url = f"{company_page_url}?query={quote(search_query)}"
        
        print(f"  🔍 Searching MFN for {year} report: {search_url}")
        headers = {"User-Agent": get_random_user_agent()}
        resp = requests.get(search_url, headers=headers, timeout=15)
        
        if resp.status_code != 200:
            print(f"    ✗ HTTP {resp.status_code}")
            return []
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Look for links to report pages
        # Pattern: https://mfn.se/cis/a/{company}/...
        report_links = []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            
            # Check if this is a report link
            if '/cis/' in href:
                # Make absolute URL
                abs_url = urljoin(search_url, href)
                
                # Filter for annual reports
                combined = f"{href} {text}".lower()
                
                # Check for annual report keywords
                is_annual_report = any(kw in combined for kw in [
                    'annual report', 'årsredovisning', 'annual', 'year-end', 
                    'publishes', 'report', str(year)
                ])
                
                # Exclude quarterly reports
                is_quarterly = any(kw in combined for kw in [
                    'q1', 'q2', 'q3', 'q4', 'quarter', 'interim', 'delårs', 'kvartals'
                ])
                
                if is_annual_report and not is_quarterly:
                    # Extra check: year should be in the link or text
                    if str(year) in combined:
                        report_links.append(abs_url)
                        print(f"    ✓ Found potential report link: {text[:60]}")
        
        return report_links
    
    except Exception as e:
        print(f"    ✗ Error searching MFN: {e}")
        return []


def extract_cision_attachments(report_page_url):
    """
    Extract Cision PDF attachments from MFN report page.
    
    Args:
        report_page_url: MFN report page URL (e.g., https://mfn.se/cis/a/hexagon/...)
    
    Returns:
        List of PDF URLs found
    """
    try:
        print(f"  📄 Extracting attachments from: {report_page_url}")
        headers = {"User-Agent": get_random_user_agent()}
        resp = requests.get(report_page_url, headers=headers, timeout=15)
        
        if resp.status_code != 200:
            print(f"    ✗ HTTP {resp.status_code}")
            return []
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Look for Cision links (mb.cision.com)
        pdf_links = []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            
            # Check for Cision PDF links
            if 'cision.com' in href and '.pdf' in href.lower():
                # Make absolute URL
                abs_url = urljoin(report_page_url, href)
                pdf_links.append(abs_url)
                print(f"    ✓ Found Cision PDF: {abs_url}")
        
        # Also look for direct PDF links
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if href.lower().endswith('.pdf') and href not in pdf_links:
                # Exclude already found links
                abs_url = urljoin(report_page_url, href)
                if abs_url not in pdf_links:
                    pdf_links.append(abs_url)
                    print(f"    ✓ Found direct PDF: {abs_url}")
        
        if not pdf_links:
            print(f"    ⚠ No PDF attachments found on page")
        
        return pdf_links
    
    except Exception as e:
        print(f"    ✗ Error extracting attachments: {e}")
        return []


def find_reports_via_mfn(company_name, years):
    """
    Search MFN.se for annual reports for a company.
    
    This is a fallback method when standard IR page search fails.
    
    Args:
        company_name: Company name (e.g., "Hexagon AB")
        years: List of years to search for (e.g., [2020, 2021])
    
    Returns:
        List of dicts: [{'year': 2020, 'url': 'https://...', 'title': '...', 'source': 'mfn'}]
    """
    print(f"  🌐 Trying MFN search for {company_name}...")
    
    # Find company page on MFN
    company_page = find_mfn_company_page(company_name)
    if not company_page:
        return []
    
    results = []
    
    # Search for each year
    for year in years:
        print(f"\n  📅 Searching for {year} report...")
        
        # Search for report links
        report_links = search_mfn_for_report(company_page, year)
        
        if not report_links:
            print(f"    ✗ No report links found for {year}")
            continue
        
        # Extract PDFs from each report page
        for report_link in report_links[:3]:  # Limit to first 3 results
            pdf_urls = extract_cision_attachments(report_link)
            
            # Add each PDF as a candidate
            for pdf_url in pdf_urls:
                results.append({
                    'year': year,
                    'url': pdf_url,
                    'title': f'Annual Report {year} (MFN/Cision)',
                    'source_page': report_link,
                    'source': 'mfn'
                })
            
            # Small delay between requests
            time.sleep(0.5)
    
    if results:
        print(f"\n  ✓ MFN search found {len(results)} potential reports")
    else:
        print(f"\n  ✗ MFN search found no reports")
    
    return results


def test_mfn_search():
    """Test MFN search with Hexagon example."""
    print("="*80)
    print("Testing MFN search with Hexagon")
    print("="*80)
    
    results = find_reports_via_mfn("Hexagon AB", [2020])
    
    if results:
        print(f"\n✓ SUCCESS: Found {len(results)} reports")
        for r in results:
            print(f"  Year: {r['year']}")
            print(f"  URL: {r['url']}")
            print(f"  Source: {r['source_page']}")
            print()
    else:
        print("\n✗ No reports found")


if __name__ == "__main__":
    # Run test when module is executed directly
    test_mfn_search()
