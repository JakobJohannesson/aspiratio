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
        company_name: Company name (e.g., "Hexagon AB", "Alfa Laval")
    
    Returns:
        Normalized name for URL (e.g., "hexagon", "alfa-laval")
    """
    # Known company mappings for MFN URLs
    known_mappings = {
        'alfa laval': 'alfa-laval',
        'atlas copco': 'atlas-copco',
        'assa abloy': 'assa-abloy',
        'sv. handelsbanken': 'handelsbanken',
        'svenska handelsbanken': 'handelsbanken',
        'handelsbanken': 'handelsbanken',
        'nibe industrier': 'nibe-industrier',
        'telia company': 'telia-company',
        'swedish match': 'swedish-match',
        # Banks - need special handling
        'nordea bank abp': 'nordea-bank',
        'nordea bank': 'nordea-bank',
        'nordea': 'nordea-bank',
        'seb': 'seb',
        'seb a': 'seb',
        'skandinaviska enskilda banken': 'seb',
    }
    
    # Remove common suffixes
    name = re.sub(r'\s+(ab|ltd|corp|inc|group|abp|as|asa|sa|nv|plc|b|a)$', '', company_name, flags=re.IGNORECASE)
    name = name.strip().lower()
    
    # Check known mappings
    if name in known_mappings:
        return known_mappings[name]
    
    # Remove special characters except spaces
    name = re.sub(r'[^a-z0-9\s-]', '', name)
    
    # Replace spaces with hyphens (common MFN pattern)
    name_hyphen = name.replace(' ', '-')
    
    # Also try first word only
    name_first = name.split()[0] if name.split() else name
    
    return name_hyphen  # Return hyphenated version as default


def find_mfn_company_page(company_name):
    """
    Find the MFN page for a company.
    
    Tries multiple URL patterns to find the company's MFN page.
    
    Args:
        company_name: Company name to search for
    
    Returns:
        MFN URL if found, None otherwise
    """
    normalized_name = normalize_company_name(company_name)
    
    # Also try first word only as alternative
    name_parts = re.sub(r'[^a-z0-9\s]', '', company_name.lower()).split()
    first_word = name_parts[0] if name_parts else normalized_name
    
    # URLs to try
    url_variants = [
        f"https://mfn.se/all/a/{normalized_name}",  # Full hyphenated name
        f"https://mfn.se/all/a/{first_word}",        # First word only
    ]
    
    # Remove duplicates while preserving order
    url_variants = list(dict.fromkeys(url_variants))
    
    headers = {"User-Agent": get_random_user_agent()}
    
    for test_url in url_variants:
        try:
            print(f"  🔍 Trying MFN URL: {test_url}")
            resp = requests.get(test_url, headers=headers, timeout=15, allow_redirects=True)
            
            if resp.status_code == 200:
                # Verify this is a company page (not a 404 soft page)
                soup = BeautifulSoup(resp.text, 'html.parser')
                # Check for company indicators or news feed items
                if soup.find('h1') or soup.find(class_=re.compile(r'company|ticker', re.I)) or soup.find_all(href=re.compile(r'/cis/')):
                    print(f"    ✓ Found MFN company page")
                    return test_url
        except Exception as e:
            print(f"    ✗ Error checking URL: {e}")
    
    print(f"    ✗ Could not find MFN page for {company_name}")
    return None


def scan_mfn_feed_for_reports(company_page_url, years):
    """
    Scan the MFN news feed for annual report PDFs.
    
    This method directly scans the news feed on the MFN company page
    for press releases announcing annual reports, then follows the
    detail page links to extract the embedded Cision or storage.mfn.se PDF links.
    
    Args:
        company_page_url: MFN company page URL (e.g., https://mfn.se/all/a/alfa-laval)
        years: List of years to search for
    
    Returns:
        List of dicts: [{'year': 2020, 'url': 'https://storage.mfn.se/...', ...}]
    """
    results = []
    found_years = set()
    
    try:
        # Add limit parameter to get more results - use large limit to reach older reports (2019, 2020)
        feed_url = f"{company_page_url}?query&limit=100000"
        print(f"  📡 Scanning MFN feed: {feed_url}")
        headers = {"User-Agent": get_random_user_agent()}
        resp = requests.get(feed_url, headers=headers, timeout=20)
        
        if resp.status_code != 200:
            print(f"    ✗ HTTP {resp.status_code}")
            return []
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Keywords for annual reports in Swedish and English
        annual_keywords = [
            'annual report', 'årsredovisning', 'year-end report',
            'bokslutskommuniké', 'annual and sustainability report',
            'års- och hållbarhetsredovisning', 'annual reporting',
            'publishes the annual', 'published its annual',
            'publicerar årsredovisning', 'års- och koncernredovisning'
        ]
        
        # Keywords to exclude (quarterly reports)
        exclude_keywords = [
            'q1', 'q2', 'q3', 'q4', 'quarter', 'interim', 
            'delårs', 'kvartals', 'halvårs', 'january-march',
            'january-june', 'january-september', 'april-june',
            'july-september', 'october-december'
        ]
        
        # First check for direct PDF links on the main page
        # Look for storage.mfn.se, cision.com, and globenewswire PDFs
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            
            # Check if this is a PDF link from known sources
            is_pdf = '.pdf' in href.lower()
            is_known_source = any(s in href for s in ['cision.com', 'storage.mfn.se', 'globenewswire.com'])
            if is_pdf and is_known_source:
                # Get the parent element to find context
                parent = link.find_parent()
                context = parent.get_text(strip=True).lower() if parent else text
                
                # Check if it's an annual report (not quarterly)
                is_annual = any(kw in context for kw in annual_keywords)
                is_quarterly = any(kw in context for kw in exclude_keywords)
                
                if is_annual and not is_quarterly:
                    # Try to extract year from context
                    for year in years:
                        if year not in found_years and (str(year) in context or str(year) in href):
                            results.append({
                                'year': year,
                                'url': href,
                                'title': f'Annual Report {year} (via MFN)',
                                'source_page': company_page_url,
                                'source': 'mfn_feed'
                            })
                            found_years.add(year)
                            print(f"    ✓ Found {year} report (direct): {href[:70]}...")
                            break
        
        # Now find and follow links to report detail pages
        # Look for both /cis/ (older) and /a/ (newer) patterns
        detail_pages_to_check = []
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            
            # Match both old (/cis/) and new (/a/) MFN URL patterns
            # Also match /one/a/ pattern
            is_detail_page = '/cis/' in href or ('/a/' in href and '/all/a/' not in href) or '/one/a/' in href
            if is_detail_page:
                combined = f"{href} {text}".lower()
                
                # Check for annual report keywords
                is_annual = any(kw in combined for kw in annual_keywords)
                is_quarterly = any(kw in combined for kw in exclude_keywords)
                
                if is_annual and not is_quarterly:
                    for year in years:
                        if year not in found_years and str(year) in combined:
                            abs_url = href if href.startswith('http') else f"https://mfn.se{href}"
                            detail_pages_to_check.append((year, abs_url, text[:80]))
                            break
        
        # Follow detail pages to extract PDFs
        for year, detail_url, title in detail_pages_to_check[:10]:  # Limit to 10 pages
            if year in found_years:
                continue
            
            print(f"    📄 Checking detail page for {year}: {title}...")
            pdf_urls = extract_cision_attachments(detail_url)
            
            if pdf_urls:
                # Take the first PDF (usually the main annual report)
                for pdf_url in pdf_urls[:2]:  # Take up to 2 PDFs per page
                    results.append({
                        'year': year,
                        'url': pdf_url,
                        'title': f'Annual Report {year} (via MFN)',
                        'source_page': detail_url,
                        'source': 'mfn_detail'
                    })
                found_years.add(year)
                print(f"      ✓ Found {year} report PDF")
            
            time.sleep(0.3)  # Small delay between requests
        
        if results:
            print(f"    ✓ Found {len(results)} annual reports from feed scan")
        else:
            print(f"    ⚠ No annual reports found in feed")
            
    except Exception as e:
        print(f"    ✗ Error scanning feed: {e}")
    
    return results


def search_mfn_for_report(company_page_url, year):
    """
    Search MFN company page for annual report for a specific year.
    
    Tries multiple search queries to find the annual report announcement.
    
    Args:
        company_page_url: MFN company page URL
        year: Year to search for (e.g., 2020)
    
    Returns:
        List of report page URLs found
    """
    try:
        headers = {"User-Agent": get_random_user_agent()}
        
        # Try multiple search queries
        search_queries = [
            f"{year} annual report",
            f"årsredovisning {year}",
            f"annual reporting {year}",
            f"publishes annual {year}",
        ]
        
        report_links = []
        
        for search_query in search_queries:
            search_url = f"{company_page_url}?query={quote(search_query)}"
            
            print(f"  🔍 Searching MFN: {search_query}")
            resp = requests.get(search_url, headers=headers, timeout=15)
            
            if resp.status_code != 200:
                continue
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Look for links to report pages
            # Match both old (/cis/) and new (/a/, /one/a/) patterns
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                # Check if this is a report detail link
                is_detail_page = '/cis/' in href or ('/a/' in href and '/all/a/' not in href) or '/one/a/' in href
                if is_detail_page:
                    # Make absolute URL
                    abs_url = urljoin(search_url, href)
                    
                    # Already found this link?
                    if abs_url in report_links:
                        continue
                    
                    combined = f"{href} {text}".lower()
                    
                    # Check for annual report keywords
                    is_annual_report = any(kw in combined for kw in [
                        'annual report', 'årsredovisning', 'annual', 'year-end', 
                        'publishes', 'published', 'annual reporting'
                    ])
                    
                    # Exclude quarterly reports
                    is_quarterly = any(kw in combined for kw in [
                        'q1', 'q2', 'q3', 'q4', 'quarter', 'interim', 
                        'delårs', 'kvartals', 'january-march', 'january-june',
                        'january-september', 'april-june', 'july-september'
                    ])
                    
                    # Year should be in the link or text
                    has_year = str(year) in combined
                    
                    if is_annual_report and not is_quarterly and has_year:
                        report_links.append(abs_url)
                        print(f"    ✓ Found potential report: {text[:60]}")
            
            # If we found something, don't try other queries
            if report_links:
                break
            
            time.sleep(0.3)
        
        return report_links
    
    except Exception as e:
        print(f"    ✗ Error searching MFN: {e}")
        return []


def extract_cision_attachments(report_page_url):
    """
    Extract PDF attachments from MFN report page.
    
    Looks for PDFs from:
    - storage.mfn.se (newer MFN pages)
    - mb.cision.com (Cision-hosted PDFs)
    - globenewswire.com (GlobeNewswire PDFs)
    
    Args:
        report_page_url: MFN report page URL (e.g., https://mfn.se/a/company/...)
    
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
        
        # Look for PDF links from known sources
        pdf_links = []
        known_pdf_sources = ['storage.mfn.se', 'cision.com', 'globenewswire.com', 'ml-eu.globenewswire.com']
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            
            # Check for PDF links from known sources
            is_pdf = '.pdf' in href.lower()
            is_known_source = any(s in href for s in known_pdf_sources)
            
            if is_pdf and is_known_source:
                # Make absolute URL
                if href.startswith('//'):
                    abs_url = 'https:' + href
                elif href.startswith('http'):
                    abs_url = href
                else:
                    abs_url = urljoin(report_page_url, href)
                
                if abs_url not in pdf_links:
                    pdf_links.append(abs_url)
                    print(f"    ✓ Found PDF: {abs_url[:70]}...")
        
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
    Uses two strategies:
    1. Scan the news feed for annual report announcements with embedded PDFs
    2. Search for each year individually (slower, more thorough)
    
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
    found_years = set()
    
    # Strategy 1: Scan feed for all years at once (faster)
    print(f"\n  📡 Strategy 1: Scanning news feed...")
    feed_results = scan_mfn_feed_for_reports(company_page, years)
    if feed_results:
        results.extend(feed_results)
        found_years = {r['year'] for r in feed_results}
        print(f"    ✓ Found reports for years: {sorted(found_years)}")
    
    # Strategy 2: Search for remaining years individually (slower but more thorough)
    remaining_years = [y for y in years if y not in found_years]
    if remaining_years:
        print(f"\n  🔍 Strategy 2: Searching for remaining years {remaining_years}...")
        for year in remaining_years:
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
