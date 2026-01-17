"""
Cision News search source for annual reports.

This module provides functionality to search for annual reports on news.cision.com,
which is the primary source for Swedish company press releases and report PDFs.

Example flow for Nordea:
1. Find company page: https://news.cision.com/nordea
2. Search for reports: https://news.cision.com/nordea/?q=annual%20report
3. Find report detail page: https://news.cision.com/nordea/r/nordea-has-published-its-annual-reporting-for-2024,c4109844
4. Extract PDF URL: https://mb.cision.com/Main/434/4109844/3280270.pdf
"""
import re
import requests
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup
import time


def get_random_user_agent():
    """Return a user agent string."""
    return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


# Some companies require the /se/ prefix on Cision URLs
SE_PREFIX_COMPANIES = {
    'h---m-hennes---mauritz-ab',
    'boliden',
    'electrolux',
    'ericsson',
    'investor',
}


def normalize_company_name_for_cision(company_name):
    """
    Normalize company name for Cision News URL.
    
    Args:
        company_name: Company name (e.g., "Nordea Bank Abp", "SEB A")
    
    Returns:
        Tuple of (normalized_name, uses_se_prefix)
    """
    # Known company mappings for Cision URLs
    # Format: (url_slug, uses_se_prefix)
    known_mappings = {
        'nordea bank abp': ('nordea', False),
        'nordea bank': ('nordea', False),
        'nordea': ('nordea', False),
        'seb a': ('seb', False),
        'seb': ('seb', False),
        'skandinaviska enskilda banken': ('seb', False),
        'sv. handelsbanken': ('handelsbanken', False),
        'svenska handelsbanken': ('handelsbanken', False),
        'handelsbanken': ('handelsbanken', False),
        'alfa laval': ('alfa-laval', False),
        'atlas copco': ('atlas-copco', False),
        'assa abloy': ('assa-abloy', False),
        'nibe industrier': ('nibe-industrier', False),
        'telia company': ('telia-company', False),
        'hexagon': ('hexagon', False),
        'volvo': ('volvo', False),
        'ericsson': ('ericsson', True),
        'sandvik': ('sandvik', False),
        'skf': ('skf', False),
        'electrolux': ('electrolux', True),
        'investor': ('investor', True),
        'swedbank': ('swedbank', False),
        'boliden': ('boliden', True),
        'epiroc': ('epiroc', False),
        'essity': ('essity', False),
        'getinge': ('getinge', False),
        'evolution': ('evolution', False),
        'eqt': ('eqt', False),
        # H&M has special URL format
        'h & m': ('h---m-hennes---mauritz-ab', True),
        'h&m': ('h---m-hennes---mauritz-ab', True),
        'hennes & mauritz': ('h---m-hennes---mauritz-ab', True),
        'hennes mauritz': ('h---m-hennes---mauritz-ab', True),
        'h m': ('h---m-hennes---mauritz-ab', True),
    }
    
    # Remove common suffixes
    name = re.sub(r'\s+(ab|ltd|corp|inc|group|abp|as|asa|sa|nv|plc|b|a)$', '', company_name, flags=re.IGNORECASE)
    name = name.strip().lower()
    
    # Check known mappings
    if name in known_mappings:
        return known_mappings[name]  # Returns (slug, uses_se_prefix)
    
    # Remove special characters except spaces and hyphens
    slug = re.sub(r'[^a-z0-9\s-]', '', name)
    
    # Replace spaces with hyphens
    slug = slug.replace(' ', '-')
    
    # Check if this slug needs /se/ prefix
    uses_se = slug in SE_PREFIX_COMPANIES
    
    return (slug, uses_se)


def find_cision_company_page(company_name):
    """
    Find the Cision News page for a company.
    
    Args:
        company_name: Company name to search for
    
    Returns:
        Cision News URL if found, None otherwise
    """
    slug, uses_se_prefix = normalize_company_name_for_cision(company_name)
    
    # Also try first word only as alternative
    name_parts = re.sub(r'[^a-z0-9\s]', '', company_name.lower()).split()
    first_word = name_parts[0] if name_parts else slug
    
    # Build URLs to try - prefer /se/ prefix if specified
    url_variants = []
    
    if uses_se_prefix:
        # Try /se/ prefix first for Swedish companies
        url_variants.append(f"https://news.cision.com/se/{slug}")
        url_variants.append(f"https://news.cision.com/{slug}")  # Fallback without /se/
    else:
        # Try without /se/ first
        url_variants.append(f"https://news.cision.com/{slug}")
        url_variants.append(f"https://news.cision.com/se/{slug}")  # Try with /se/ as fallback
    
    # Also try first word variants
    if first_word != slug:
        url_variants.append(f"https://news.cision.com/{first_word}")
        url_variants.append(f"https://news.cision.com/se/{first_word}")
    
    # Remove duplicates while preserving order
    url_variants = list(dict.fromkeys(url_variants))
    
    headers = {"User-Agent": get_random_user_agent()}
    
    for test_url in url_variants:
        try:
            print(f"  🔍 Trying Cision URL: {test_url}")
            resp = requests.get(test_url, headers=headers, timeout=15, allow_redirects=True)
            
            if resp.status_code == 200:
                # Verify this is a company page
                soup = BeautifulSoup(resp.text, 'html.parser')
                # Check for company indicators
                if soup.find('h1') or soup.find(class_=re.compile(r'company|news', re.I)):
                    print(f"    ✓ Found Cision company page")
                    return test_url
        except Exception as e:
            print(f"    ✗ Error checking URL: {e}")
    
    print(f"    ✗ Could not find Cision page for {company_name}")
    return None


def search_cision_for_annual_reports(company_page_url, years):
    """
    Search Cision News for annual report announcements.
    
    Args:
        company_page_url: Cision company page URL (e.g., https://news.cision.com/nordea)
        years: List of years to search for
    
    Returns:
        List of dicts with report detail page URLs for each year found
    """
    results = []
    
    # Keywords that indicate an actual annual report release (not corrections)
    publish_keywords = [
        'publishes the annual', 'published its annual', 'has published',
        'publicerar årsredovisning', 'annual report for', 'annual reporting for',
        'releases annual', 'publicerar års', 'annual and sustainability report for',
        'annual report,', 'annual report 20'
    ]
    
    # Keywords that indicate corrections or amendments (to deprioritize)
    correction_keywords = [
        'correction', 'amendment', 'revised', 'update to', 'korrigering',
        'rättelse', 'esef file'
    ]
    
    # Keywords to exclude (quarterly reports)
    exclude_keywords = [
        'q1', 'q2', 'q3', 'q4', 'quarter', 'interim', 
        'delårs', 'kvartals', 'halvårs', 'january-march',
        'january-june', 'january-september', 'april-june',
        'july-september', 'october-december'
    ]
    
    def extract_report_year(text, href):
        """Extract the actual report year from announcement text.
        
        Looks for patterns like 'for 2024', 'för 2024', 'report 2024'.
        Returns the year if found, None otherwise.
        """
        import re
        text_lower = text.lower()
        
        # Pattern: "for 2024", "för 2024", "report 2024", "year 2024", "redovisning 2024"
        year_patterns = [
            r'for\s+(20\d{2})',
            r'för\s+(20\d{2})',
            r'report[s]?\s+(20\d{2})',
            r'reporting\s+(20\d{2})',
            r'redovisning[en]?\s+(20\d{2})',  # Covers årsredovisning, hållbarhetsredovisning, etc.
            r'redovisning[en]?\s+för\s+(20\d{2})',
            r'annual\s+report[s]?\s+(20\d{2})',
            r'year\s+(20\d{2})',
            r'financial\s+year\s+(20\d{2})',
            r'helår[et]?\s+(20\d{2})',  # "helåret 2024"
            r'[-/](20\d{2})\b',  # Match year at end of slug like "-2024"
        ]
        
        for pattern in year_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return int(match.group(1))
        
        # Fallback: check URL for year in the slug
        for pattern in year_patterns:
            match = re.search(pattern, href.lower())
            if match:
                return int(match.group(1))
        
        return None
    
    try:
        headers = {"User-Agent": get_random_user_agent()}
        found_years = set()
        all_candidates = []  # Store all candidates per year, sorted by priority
        
        # Build list of URLs to search
        # Start with ?m=Financial filter (most efficient - gets financial reports only)
        search_urls = [
            f"{company_page_url}/?m=Financial",  # Financial filter - best for annual reports
        ]
        
        # Add search queries as fallback
        search_queries = [
            "annual%20report",
            "publishes%20annual",
            "årsredovisning",
        ]
        
        for search_query in search_queries:
            search_urls.append(f"{company_page_url}/?q={search_query}")
        
        # Add year-specific queries for years not found
        for year in years:
            search_urls.append(f"{company_page_url}/?q=annual%20report%20{year}")
            search_urls.append(f"{company_page_url}/?q=årsredovisning%20{year}")
        
        seen_urls = set()
        
        for search_url in search_urls:
            print(f"  🔍 Searching Cision: {search_url}")
            
            resp = requests.get(search_url, headers=headers, timeout=20)
            
            if resp.status_code != 200:
                continue
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Find all links on the page that might be report announcements
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                # Check if this is a report detail page link
                # Pattern: /company/r/title-slug,c1234567
                if '/r/' in href and ',c' in href:
                    # Skip if we've already seen this URL
                    abs_url = href if href.startswith('http') else f"https://news.cision.com{href}"
                    if abs_url in seen_urls:
                        continue
                    seen_urls.add(abs_url)
                    
                    combined = f"{href} {text}".lower()
                    
                    # Skip quarterly reports
                    is_quarterly = any(kw in combined for kw in exclude_keywords)
                    if is_quarterly:
                        continue
                    
                    # Extract the actual report year from the title
                    report_year = extract_report_year(text, href)
                    
                    if report_year and report_year in years:
                        # Check if this is an annual report announcement
                        is_publish = any(kw in combined for kw in publish_keywords)
                        is_correction = any(kw in combined for kw in correction_keywords)
                        
                        # Calculate priority (lower is better)
                        if is_publish and not is_correction:
                            priority = 1  # Best: actual publication
                        elif is_publish and is_correction:
                            priority = 3  # Correction to publication
                        elif not is_correction:
                            priority = 2  # Other annual report mention
                        else:
                            priority = 4  # Correction only
                        
                        all_candidates.append({
                            'year': report_year,
                            'detail_url': abs_url,
                            'title': text[:100],
                            'priority': priority
                        })
            
            time.sleep(0.2)
        
        # Sort candidates by year and priority, then pick the best for each year
        all_candidates.sort(key=lambda x: (x['year'], x['priority']))
        
        for candidate in all_candidates:
            year = candidate['year']
            if year not in found_years:
                results.append(candidate)
                found_years.add(year)
                print(f"    ✓ Found {year} report (priority {candidate['priority']}): {candidate['title'][:50]}...")
        
        if results:
            print(f"    ✓ Found {len(results)} annual report announcements")
        else:
            print(f"    ⚠ No annual report announcements found")
            
    except Exception as e:
        print(f"    ✗ Error searching Cision: {e}")
    
    return results


def extract_pdf_from_cision_detail(detail_url):
    """
    Extract PDF URLs from a Cision report detail page.
    
    The detail page URL contains a Cision ID (e.g., c4109844) which is used
    to construct the PDF URL pattern: mb.cision.com/Main/{company_id}/{cision_id}/{file_id}.pdf
    
    Args:
        detail_url: Cision detail page URL (e.g., https://news.cision.com/nordea/r/...,c4109844)
    
    Returns:
        List of PDF URLs found
    """
    try:
        print(f"  📄 Extracting PDFs from: {detail_url}")
        headers = {"User-Agent": get_random_user_agent()}
        resp = requests.get(detail_url, headers=headers, timeout=15)
        
        if resp.status_code != 200:
            print(f"    ✗ HTTP {resp.status_code}")
            return []
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        pdf_urls = []
        
        # Look for Cision PDF links (mb.cision.com)
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            
            # Check for Cision PDF links
            if 'cision.com' in href and '.pdf' in href.lower():
                abs_url = href if href.startswith('http') else f"https:{href}"
                if abs_url not in pdf_urls:
                    pdf_urls.append(abs_url)
                    print(f"    ✓ Found PDF: {abs_url}")
        
        # Also look for any direct PDF links
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if href.lower().endswith('.pdf'):
                abs_url = urljoin(detail_url, href)
                if abs_url not in pdf_urls:
                    pdf_urls.append(abs_url)
                    print(f"    ✓ Found direct PDF: {abs_url}")
        
        if not pdf_urls:
            print(f"    ⚠ No PDF links found on page")
        
        return pdf_urls
    
    except Exception as e:
        print(f"    ✗ Error extracting PDFs: {e}")
        return []


def find_reports_via_cision(company_name, years):
    """
    Search Cision News for annual reports for a company.
    
    This is the primary method for finding Swedish company annual reports.
    
    Args:
        company_name: Company name (e.g., "Nordea Bank Abp")
        years: List of years to search for (e.g., [2020, 2021, 2022])
    
    Returns:
        List of dicts: [{'year': 2020, 'url': 'https://mb.cision.com/...', 'title': '...', 'source': 'cision'}]
    """
    print(f"  🌐 Searching Cision News for {company_name}...")
    
    # Find company page on Cision
    company_page = find_cision_company_page(company_name)
    if not company_page:
        return []
    
    results = []
    
    # Search for annual report announcements
    announcements = search_cision_for_annual_reports(company_page, years)
    
    if not announcements:
        print(f"  ✗ No annual report announcements found")
        return []
    
    # Extract PDFs from each announcement page
    for announcement in announcements:
        year = announcement['year']
        detail_url = announcement['detail_url']
        title = announcement.get('title', f'Annual Report {year}')
        
        print(f"\n  📅 Processing {year} report...")
        pdf_urls = extract_pdf_from_cision_detail(detail_url)
        
        if pdf_urls:
            # Add each PDF as a candidate (first one is usually the main report)
            for i, pdf_url in enumerate(pdf_urls[:2]):  # Take up to 2 PDFs
                results.append({
                    'year': year,
                    'url': pdf_url,
                    'title': title if i == 0 else f"{title} (attachment {i+1})",
                    'source_page': detail_url,
                    'source': 'cision'
                })
        
        time.sleep(0.3)  # Small delay between requests
    
    if results:
        print(f"\n  ✓ Cision search found {len(results)} PDF candidates")
    else:
        print(f"\n  ✗ Cision search found no PDFs")
    
    return results


def test_cision_search():
    """Test Cision search with Nordea example."""
    print("="*80)
    print("Testing Cision search with Nordea")
    print("="*80)
    
    results = find_reports_via_cision("Nordea Bank Abp", [2024, 2023, 2022])
    
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
    test_cision_search()
