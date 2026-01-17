"""
Annual report discovery and download utilities.
"""
import re
import os
import requests
import random
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
import time
from datetime import datetime

# Import connection error utilities
from ..common.connection_errors import categorize_connection_error, format_error_message

# Import MFN search for fallback
from ..tier1.mfn_search import find_reports_via_mfn

# User agents to rotate through
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

class DownloadError(Exception):
    """Raised when download fails after multiple retries."""
    pass

def get_random_user_agent():
    """Return a random user agent from the pool."""
    return random.choice(USER_AGENTS)

def extract_pdf_from_html_page(url, year_hint=None):
    """
    Extract PDF download link from an HTML page.
    Handles cases where URL points to an HTML page containing the actual PDF link.
    
    Args:
        url: URL of HTML page
        year_hint: Optional year to help identify correct PDF
    
    Returns:
        PDF URL if found, otherwise None
    """
    try:
        headers = {"User-Agent": get_random_user_agent()}
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return None
        
        # Check if this is actually a PDF
        content_type = response.headers.get('Content-Type', '').lower()
        if 'application/pdf' in content_type:
            return url  # It's already a PDF
        
        # Parse HTML to find PDF links
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for PDF download links
        pdf_links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            
            # Check if this looks like a PDF link
            if '.pdf' in href.lower() or 'pdf' in text:
                # Filter for annual report keywords
                if any(kw in text or kw in href.lower() for kw in ['annual', 'report', 'entire', 'full']):
                    # Make absolute URL
                    abs_url = urljoin(url, href)
                    pdf_links.append(abs_url)
        
        if pdf_links:
            # If year hint provided, try to find matching PDF
            if year_hint:
                for pdf_url in pdf_links:
                    if str(year_hint) in pdf_url:
                        print(f"    → Found PDF link on HTML page: {pdf_url}")
                        return pdf_url
            
            # Return first PDF found
            print(f"    → Found PDF link on HTML page: {pdf_links[0]}")
            return pdf_links[0]
        
    except Exception as e:
        print(f"    ✗ Error extracting PDF from HTML: {e}")
    
    return None

def try_direct_url_patterns(ir_url, years):
    """
    Try known direct URL patterns for specific companies.
    Some sites have predictable patterns but JavaScript-rendered links.
    
    Args:
        ir_url: Investor relations URL
        years: List of years to check
    
    Returns:
        List of dicts: [{'year': 2024, 'url': 'https://...', 'title': '...'}]
    """
    results = []
    netloc = urlparse(ir_url).netloc
    headers = {"User-Agent": get_random_user_agent()}
    
    # ASSA ABLOY pattern
    if 'assaabloy.com' in netloc:
        print("  Detected ASSA ABLOY - trying direct PDF pattern...")
        # Try both capitalizations (changed between years)
        patterns = [
            "https://www.assaabloy.com/group/en/documents/investors/annual-reports/{year}/Annual%20Report%20{year}.pdf",
            "https://www.assaabloy.com/group/en/documents/investors/annual-reports/{year}/Annual%20report%20{year}.pdf",
        ]
        
        for year in years:
            found = False
            for pattern in patterns:
                pdf_url = pattern.format(year=year)
                try:
                    resp = requests.head(pdf_url, headers=headers, timeout=10, allow_redirects=True)
                    if resp.status_code == 200:
                        results.append({
                            'year': year,
                            'url': pdf_url,
                            'title': f'Annual Report {year}',
                            'source_page': ir_url
                        })
                        print(f"    ✓ Found {year} via direct URL")
                        found = True
                        break
                except Exception as e:
                    continue
            
            if not found:
                print(f"    ✗ {year}: Not found")
    
    # ABB pattern - use search but exclude SEC filings
    if 'abb.com' in netloc or 'abb' in netloc:
        print("  Detected ABB - will search for Group Annual Reports (excluding SEC filings)...")
        # Let the main search handle it, but we'll filter in the search logic
    
    return results

def extract_links_from_page(url, soup):
    """
    Extract all links from a page including those in JSON data structures,
    navigation bars, and footer sections.
    
    Args:
        url: Base URL for making relative links absolute
        soup: BeautifulSoup object of the page
    
    Returns:
        List of dicts: [{'href': '...', 'text': '...', 'title': '...', 'source': '...'}]
    """
    all_links = []
    
    # 1. Regular HTML links
    for link in soup.find_all('a', href=True):
        all_links.append({
            'href': link.get('href', ''),
            'text': link.get_text(strip=True).lower(),
            'title': link.get('title', '').lower(),
            'source': 'html'
        })
    
    # 2. Check for JSON-LD structured data (common for IR pages)
    import json
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
            # Recursively find URLs in JSON
            def extract_urls(obj, path=''):
                if isinstance(obj, dict):
                    for key, val in obj.items():
                        if key.lower() in ['url', 'contenturl', 'link', 'href']:
                            if isinstance(val, str) and val.startswith('http'):
                                all_links.append({
                                    'href': val,
                                    'text': obj.get('name', obj.get('headline', '')).lower() if isinstance(obj.get('name'), str) else '',
                                    'title': obj.get('description', '').lower() if isinstance(obj.get('description'), str) else '',
                                    'source': f'json-ld:{path}'
                                })
                        else:
                            extract_urls(val, f'{path}.{key}')
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        extract_urls(item, f'{path}[{i}]')
            extract_urls(data)
        except (json.JSONDecodeError, AttributeError):
            pass
    
    # 3. Check for navigation menus (often contain annual reports link)
    nav_elements = soup.find_all(['nav', 'header']) + soup.find_all(class_=re.compile(r'nav|menu|header', re.I))
    for nav in nav_elements:
        for link in nav.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            # Mark these as high-priority navigation links
            all_links.append({
                'href': href,
                'text': text,
                'title': link.get('title', '').lower(),
                'source': 'navigation'
            })
    
    # 4. Check footer for investor relations link (failsafe)
    footer_elements = soup.find_all(['footer']) + soup.find_all(class_=re.compile(r'footer', re.I))
    for footer in footer_elements:
        for link in footer.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            if any(kw in text or kw in href.lower() for kw in ['investor', 'ir', 'investerare', 'financial']):
                all_links.append({
                    'href': href,
                    'text': text,
                    'title': link.get('title', '').lower(),
                    'source': 'footer'
                })
    
    # 5. JavaScript data attributes (data-href, data-url, etc.)
    for elem in soup.find_all(attrs={'data-href': True}):
        all_links.append({
            'href': elem.get('data-href', ''),
            'text': elem.get_text(strip=True).lower(),
            'title': elem.get('data-title', '').lower(),
            'source': 'data-attr'
        })
    
    return all_links

def find_ir_page_from_main_site(main_url):
    """
    Failsafe: Navigate from main company page to find investor relations page.
    Looks in navigation, footer, and common patterns.
    
    Args:
        main_url: Main company website URL
    
    Returns:
        IR URL if found, otherwise None
    """
    try:
        print(f"  🔄 Failsafe: Searching main site for IR link: {main_url}")
        headers = {"User-Agent": get_random_user_agent()}
        resp = requests.get(main_url, timeout=15, headers=headers)
        
        if resp.status_code != 200:
            print(f"    ✗ HTTP {resp.status_code}")
            return None
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        links = extract_links_from_page(main_url, soup)
        
        # IR keywords to look for
        ir_keywords = ['investor', 'ir', 'investerare', 'shareholder', 'financial', 'annual report']
        
        # Prioritize footer and navigation links
        for priority_source in ['footer', 'navigation', 'html']:
            for link in links:
                if link['source'] != priority_source:
                    continue
                
                combined = f"{link['href']} {link['text']} {link['title']}".lower()
                
                # Check if this looks like an IR link
                if any(kw in combined for kw in ir_keywords):
                    # Exclude press/news pages
                    if not any(bad in combined for bad in ['press', 'news', 'media', 'blog', 'article']):
                        abs_url = urljoin(main_url, link['href'])
                        print(f"    ✓ Found IR link in {link['source']}: {link['text'][:50]}")
                        print(f"      URL: {abs_url}")
                        return abs_url
        
        # Try common patterns if nothing found
        parsed = urlparse(main_url)
        common_paths = ['/investors', '/investor-relations', '/investerare', '/en/investors', '/group/en/investors']
        for path in common_paths:
            test_url = f"{parsed.scheme}://{parsed.netloc}{path}"
            try:
                resp = requests.head(test_url, headers=headers, timeout=10, allow_redirects=True)
                if resp.status_code == 200:
                    print(f"    ✓ Found IR page via common pattern: {path}")
                    return test_url
            except:
                continue
        
        print(f"    ✗ No IR link found on main site")
        return None
        
    except Exception as e:
        print(f"    ✗ Error searching main site: {e}")
        return None

def find_annual_reports(ir_url, years=None, max_depth=2, max_failures=3, enable_failsafe=True, company_name=None):
    """
    Search IR page for annual report PDFs with enhanced navigation strategy.
    
    Strategy:
    1. Extract all links from IR page (HTML, JSON-LD, navigation, footer)
    2. Look for annual reports in direct links and navigation
    3. Follow relevant pages to find reports
    4. FAILSAFE: If nothing found, go to main site → find IR link → retry
    5. MFN FALLBACK: If still nothing found and company_name provided, try MFN.se
    
    Args:
        ir_url: Investor relations page URL
        years: List of years to find (default: 2019-2024)
        max_depth: How many levels deep to search (default: 2)
        max_failures: Max consecutive failures before raising error (default: 3)
        enable_failsafe: Whether to try main site failsafe (default: True)
        company_name: Optional company name for MFN fallback search (default: None)
    
    Returns:
        List of dicts: [{'year': 2024, 'url': 'https://...', 'title': '...'}]
    
    Raises:
        DownloadError: If max_failures consecutive errors occur
    """
    if years is None:
        years = list(range(2019, 2025))
    
    results = []
    
    # Try direct URL patterns first (for JavaScript-heavy sites)
    direct_results = try_direct_url_patterns(ir_url, years)
    if direct_results:
        print(f"  Found {len(direct_results)} reports via direct URL patterns")
        results.extend(direct_results)
        # Remove years we already found
        years = [y for y in years if y not in [r['year'] for r in direct_results]]
        if not years:  # Found everything
            return sorted(results, key=lambda x: x['year'], reverse=True)
    
    visited = set()
    consecutive_failures = 0
    
    # Get the base domain (e.g., "abb" from "global.abb.com")
    base_netloc = urlparse(ir_url).netloc
    base_domain_parts = base_netloc.split('.')
    if len(base_domain_parts) >= 2:
        # Get last 2 parts (e.g., "abb.com")
        base_domain = '.'.join(base_domain_parts[-2:])
    else:
        base_domain = base_netloc
    
    def search_page(url, depth=0):
        nonlocal consecutive_failures
        
        # Remove fragment from URL for visiting (fragments are client-side)
        url_no_fragment = url.split('#')[0]
        
        if depth > max_depth or url_no_fragment in visited:
            return
        
        visited.add(url_no_fragment)
        
        try:
            print(f"{'  ' * depth}Searching: {url}")
            headers = {"User-Agent": get_random_user_agent()}
            
            try:
                resp = requests.get(url_no_fragment, timeout=10, headers=headers)
            except (requests.exceptions.Timeout, requests.exceptions.SSLError, 
                    requests.exceptions.ConnectionError) as e:
                consecutive_failures += 1
                error_type, error_msg, emoji = categorize_connection_error(e)
                print(f"{'  ' * depth}{format_error_message(error_type, error_msg)} (failure {consecutive_failures}/{max_failures})")
                if consecutive_failures >= max_failures:
                    raise DownloadError(f"{error_msg} - failed to fetch {max_failures} pages in a row")
                return
            
            if resp.status_code != 200:
                consecutive_failures += 1
                if resp.status_code == 403:
                    print(f"{'  ' * depth}🚫 HTTP 403 Forbidden - server blocking requests (failure {consecutive_failures}/{max_failures})")
                elif resp.status_code == 404:
                    print(f"{'  ' * depth}❌ HTTP 404 Not Found (failure {consecutive_failures}/{max_failures})")
                else:
                    print(f"{'  ' * depth}HTTP {resp.status_code} (failure {consecutive_failures}/{max_failures})")
                if consecutive_failures >= max_failures:
                    raise DownloadError(f"Failed to fetch {max_failures} pages in a row (last: HTTP {resp.status_code})")
                return
            
            # Reset failure counter on success
            consecutive_failures = 0
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Find all links on the page using enhanced extraction
            links_data = extract_links_from_page(url, soup)
            print(f"{'  ' * depth}  → Found {len(links_data)} links to analyze (from HTML, JSON, nav, footer)")
            
            # Convert to soup-like objects for compatibility
            class LinkWrapper:
                def __init__(self, data):
                    self._data = data
                def get(self, key, default=''):
                    return self._data.get(key, default)
                def get_text(self, strip=False):
                    return self._data.get('text', '')
            
            links = [LinkWrapper(ld) for ld in links_data]
            links_raw = links_data  # Keep raw data for source checking
            
            # Patterns to identify annual reports (more flexible - allow words in between)
            annual_patterns = [
                r'annual.*report',
                r'[åa]rsredovisning',  # Swedish: årsredovisning (also match ASCII 'a' in URLs)
                r'[åa]rsbericht',      # German variant with ASCII fallback
                r'rapport.*annuel',
                r'financial.*report',
                r'integrated.*report',
                r'abb.*group.*annual.*report',  # ABB Group Annual Report
            ]
            
            # Patterns to exclude (SEC filings, quarterly reports, etc.)
            exclude_patterns = [
                r'form\s*20[-\s]*f',  # SEC annual report filing
                r'form\s*sd',  # SEC conflict minerals filing
                r'proxy',
                r'10-k',
                r'8-k',
                r'q[1-4]',  # Quarterly reports (Q1, Q2, Q3, Q4)
                r'quarter',
                r'interim',
                r'delårs',  # Swedish: interim/quarterly
                r'kvartals',  # Swedish: quarterly
                r'half[-\s]?year',  # Half-year reports
                r'h[1-2]\s*20\d{2}',  # H1 2024, H2 2024
            ]
            
            # Patterns to identify pages that might contain reports
            navigation_patterns = [
                r'financial[s]?\s+(information|reports|data)',
                r'reports?\s+(and|&)?\s+presentations?',
                r'annual\s+reports?',
                r'annual\s+reporting',
                r'publications?',
                r'download[s]?',
                r'library',
                r'archive',
            ]
            
            pattern = '|'.join(annual_patterns)
            exclude_pattern = '|'.join(exclude_patterns)
            nav_pattern = '|'.join(navigation_patterns)
            
            pages_to_visit = []
            pdf_count = 0
            excluded_count = 0
            
            for i, link in enumerate(links):
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                title = link.get('title', '').lower()
                source = links_raw[i].get('source', 'html') if i < len(links_raw) else 'html'
                
                # Combine text sources
                combined = f"{href} {text} {title}".lower()
                
                # Prioritize navigation and footer links (they often have the main annual reports link)
                is_priority_link = source in ['navigation', 'footer']
                
                # Check if it's a PDF link for annual reports
                # Either URL ends with .pdf OR text mentions (PDF) OR href contains 'download' or 'pdf'
                is_pdf_link = (
                    href.lower().endswith('.pdf') or
                    '(pdf)' in text or
                    'pdf' in href.lower() or
                    'download' in href.lower()
                )
                
                if is_pdf_link:
                    pdf_count += 1
                
                # Check if this matches annual report pattern AND doesn't match exclusion pattern
                matches_annual = re.search(pattern, combined, re.IGNORECASE)
                matches_exclude = re.search(exclude_pattern, combined, re.IGNORECASE)
                
                if is_pdf_link and matches_annual:
                    if matches_exclude:
                        excluded_count += 1
                        # Show why this was excluded for transparency
                        exclude_reason = None
                        for pattern_name, pattern in [
                            ('SEC filing', r'form\s*20[-\s]*f|form\s*sd|proxy|10-k|8-k'),
                            ('Quarterly report', r'q[1-4]|quarter|interim|delårs|kvartals'),
                            ('Half-year report', r'half[-\s]?year|h[1-2]\s*20\d{2}')
                        ]:
                            if re.search(pattern, combined, re.IGNORECASE):
                                exclude_reason = pattern_name
                                break
                        if depth <= 1:  # Only show for top-level pages
                            print(f"{'  ' * depth}    ✗ Excluded: {text[:50]} ({exclude_reason or 'filtered'})")
                        continue
                    
                    # Make absolute URL
                    abs_url = urljoin(url, href)
                    
                    # PRIORITY FIX: Extract year from URL FIRST, then fall back to text
                    # This prevents mismatches where text says "2020" but URL points to different year
                    year = None
                    
                    # Try URL first - look for year in filename/path (most reliable)
                    # Match any year 2010-2025 to properly identify and skip old reports
                    url_year_match = re.search(r'[-_/](20(?:1[0-9]|2[0-5]))[-_.]', href.lower())
                    if url_year_match:
                        year = int(url_year_match.group(1))
                    else:
                        # Try URL with short year format (e.g., _24_ or -24- or _19_)
                        url_short_match = re.search(r'[-_/](1[5-9]|2[0-5])[-_.]', href.lower())
                        if url_short_match:
                            year_num = int(url_short_match.group(1))
                            year = 2000 + year_num
                    
                    # Fall back to text/title context only if URL didn't have year
                    if year is None:
                        # Try to find a 4-digit year first (more reliable)
                        full_year_match = re.search(r'\b(201[0-9]|202[0-5])\b', combined)
                        if full_year_match:
                            year = int(full_year_match.group(1))
                        else:
                            # Fall back to short year format (e.g., 24, 24-25)
                            short_year_match = re.search(r'\b(19|2[0-5])(?:[/-](19|2[0-5]))?\b', combined)
                            if short_year_match:
                                year_num = int(short_year_match.group(1))
                                year = 2000 + year_num
                    
                    if year is not None:
                        if year in years:
                            # Show what we found with URL snippet for debugging
                            url_snippet = abs_url.split('/')[-1][:40] if '/' in abs_url else abs_url[:40]
                            print(f"{'  ' * depth}    ✓ Found report: {year} - {text[:60]}")
                            if depth <= 1:  # Show URL for transparency
                                print(f"{'  ' * depth}      URL: .../{url_snippet}")
                            results.append({
                                'year': year,
                                'url': abs_url,
                                'title': link.get_text(strip=True),
                                'source_page': url
                            })
                        elif depth <= 1:
                            # Year detected but not in our target years - show why we're skipping
                            print(f"{'  ' * depth}    ⊘ Skipped: {year} (year {year} not in target years {years})")
                    elif depth <= 1 and is_pdf_link:
                        # Found a PDF link but couldn't extract year
                        print(f"{'  ' * depth}    ? No year found: {text[:50]}")
                
                # If depth allows, check for navigation links to follow
                # Prioritize navigation/footer links (they're more likely to be correct)
                if depth < max_depth and (is_priority_link or re.search(nav_pattern, combined, re.IGNORECASE)):
                    # Make absolute URL
                    abs_url = urljoin(url, href)
                    
                    # Allow following links on same domain or subdomains (e.g., global.abb.com -> library.e.abb.com)
                    link_netloc = urlparse(abs_url).netloc
                    if base_domain in link_netloc:
                        # Put priority links at front of queue
                        if is_priority_link:
                            pages_to_visit.insert(0, abs_url)
                        else:
                            pages_to_visit.append(abs_url)
            
            if pdf_count > 0:
                print(f"{'  ' * depth}  → Analyzed {pdf_count} PDF links, excluded {excluded_count} quarterly/SEC filings")
            
            # Visit relevant pages
            for next_url in pages_to_visit[:5]:  # Limit to 5 sub-pages
                search_page(next_url, depth + 1)
                time.sleep(0.5)  # Be nice to servers
        
        except DownloadError:
            # Re-raise DownloadError to propagate up
            raise
        except Exception as e:
            consecutive_failures += 1
            print(f"{'  ' * depth}Error searching {url}: {e} (failure {consecutive_failures}/{max_failures})")
            if consecutive_failures >= max_failures:
                raise DownloadError(f"Failed to fetch {max_failures} pages in a row (last error: {e})")
    
    # Start search
    search_page(ir_url, 0)
    
    # If no results found, try common URL patterns directly
    if not results:
        print("  No reports found in standard search, trying common patterns...")
        
        # Build common path patterns
        parsed = urlparse(ir_url)
        base_path = parsed.path.rstrip('/')
        
        common_paths = [
            f"{base_path}/annual-reports",
            f"{base_path}/annual-reporting-suite",
            f"{base_path}/reports-and-publications",
            f"{base_path}/arsredovisningar",  # Swedish: annual reports
            '/annual-reports',
            '/annual-reporting-suite',
            '/reports-and-publications',
            '/financial-reports/annual-reports',
            # Swedish language paths
            '/investerare/finansiella-rapporter/arsredovisningar',
            '/investors/financial-reports/annual-reports',
            '/investerare/finansiella-rapporter',
            # With language parameter
            f"{base_path}/annual-reports?lang=sv",
            f"{base_path}/arsredovisningar?lang=sv",
        ]
        
        # Reset failure counter when trying alternative patterns
        consecutive_failures = 0
        
        for path in common_paths:
            test_url = f"{parsed.scheme}://{parsed.netloc}{path}"
            if test_url not in visited:
                try:
                    search_page(test_url, 0)
                    if results:  # If we found something, stop trying
                        break
                except DownloadError:
                    # Don't let common path 404s stop us from trying failsafe
                    consecutive_failures = 0
                    continue
    
    # FAILSAFE: If still no results and failsafe is enabled, try going to main site
    if not results and enable_failsafe:
        print("  ⚠ No reports found, activating failsafe...")
        
        # Try to construct main site URL
        parsed = urlparse(ir_url)
        main_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Only try failsafe if we're not already on the root domain
        if parsed.path and parsed.path != '/':
            # Try to find IR page from main site
            new_ir_url = find_ir_page_from_main_site(main_url)
            
            if new_ir_url and new_ir_url != ir_url:
                print(f"  → Retrying search from discovered IR page: {new_ir_url}")
                # Recursive call but with failsafe disabled to prevent infinite loop
                try:
                    return find_annual_reports(new_ir_url, years, max_depth, max_failures, enable_failsafe=False, company_name=company_name)
                except Exception as e:
                    print(f"  ✗ Failsafe search also failed: {e}")
    
    # MFN FALLBACK: If still no results and company name is provided, try MFN.se
    if not results and company_name and enable_failsafe:
        print("  ⚠ Standard methods failed, trying MFN.se fallback...")
        try:
            mfn_results = find_reports_via_mfn(company_name, years)
            if mfn_results:
                results.extend(mfn_results)
                print(f"  ✓ MFN fallback found {len(mfn_results)} reports")
        except Exception as e:
            print(f"  ✗ MFN fallback failed: {e}")
    
    # Deduplicate by year (keep first occurrence)
    seen_years = set()
    unique_results = []
    for r in results:
        if r['year'] not in seen_years:
            seen_years.add(r['year'])
            unique_results.append(r)
    
    print(f"Found {len(unique_results)} annual reports")
    return sorted(unique_results, key=lambda x: x['year'], reverse=True)

def download_pdf(url, output_path, min_pages=50, max_retries=3, year_hint=None):
    """
    Download PDF and validate it meets minimum page requirement.
    
    Args:
        url: PDF URL (or HTML page containing PDF link)
        output_path: Where to save the file
        min_pages: Minimum number of pages required (default 50)
        max_retries: Maximum download attempts with user agent rotation (default 3)
        year_hint: Optional year to help identify correct PDF on HTML pages
    
    Returns:
        dict: {'success': bool, 'pages': int, 'size_mb': float, 'error': str}
    """
    result = {
        'success': False,
        'pages': 0,
        'size_mb': 0.0,
        'error': None
    }
    
    # Check if URL points to HTML page with PDF link
    actual_pdf_url = url
    if not url.lower().endswith('.pdf'):
        print(f"  → URL doesn't end with .pdf, checking if it's an HTML page...")
        pdf_from_html = extract_pdf_from_html_page(url, year_hint)
        if pdf_from_html:
            actual_pdf_url = pdf_from_html
        else:
            result['error'] = "URL is not a PDF and no PDF found on HTML page"
            print(f"  ✗ {result['error']}")
            return result
    
    temp_path = output_path + '.tmp'
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f"  Retry {attempt}/{max_retries}...")
                time.sleep(2)  # Wait before retry
            
            print(f"  → Downloading from: {actual_pdf_url}")
            headers = {"User-Agent": get_random_user_agent()}
            
            try:
                resp = requests.get(actual_pdf_url, timeout=30, headers=headers, stream=True)
            except (requests.exceptions.Timeout, requests.exceptions.SSLError,
                    requests.exceptions.ConnectionError) as e:
                error_type, error_msg, emoji = categorize_connection_error(e)
                result['error'] = error_msg
                print(f"  {format_error_message(error_type, error_msg)}")
                if attempt < max_retries - 1:
                    print(f"  → Retrying with different user agent...")
                    continue
                return result
            
            if resp.status_code != 200:
                result['error'] = f"HTTP {resp.status_code}"
                if resp.status_code == 403:
                    print(f"  🚫 HTTP 403 Forbidden - server may be blocking requests")
                elif resp.status_code == 404:
                    print(f"  ❌ HTTP 404 Not Found")
                else:
                    print(f"  ✗ HTTP error {resp.status_code}")
                if attempt < max_retries - 1:
                    print(f"  → Retrying with different user agent...")
                    continue  # Try again with different user agent
                return result
        
            print(f"  → Saving to: {output_path}")
            # Create directory if it doesn't exist
            output_dir = os.path.dirname(output_path)
            if output_dir:  # Only create if there's a directory component
                os.makedirs(output_dir, exist_ok=True)
            
            # Download to temporary file first
            temp_path = output_path + '.tmp'
            with open(temp_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Get file size
            size_bytes = os.path.getsize(temp_path)
            result['size_mb'] = size_bytes / (1024 * 1024)
            print(f"  → Downloaded: {result['size_mb']:.1f} MB")
            
            # Validate it's a valid PDF with minimum pages
            print(f"  → Validating PDF...")
            try:
                with open(temp_path, 'rb') as f:
                    pdf = PdfReader(f)
                    result['pages'] = len(pdf.pages)
                print(f"  → PDF has {result['pages']} pages")
            except Exception as e:
                result['error'] = f"PDF validation failed: {e}"
                print(f"  ✗ {result['error']}")
                os.remove(temp_path)
                if attempt < max_retries - 1:
                    continue  # Try again
                return result
            
            # Check minimum pages
            if result['pages'] < min_pages:
                result['error'] = f"Only {result['pages']} pages (min {min_pages} required)"
                print(f"  ✗ {result['error']}")
                os.remove(temp_path)
                return result
            
            # Move temp file to final location
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rename(temp_path, output_path)
            
            result['success'] = True
            print(f"  ✓ Success: {result['pages']} pages, {result['size_mb']:.1f} MB")
            return result
        
        except Exception as e:
            result['error'] = str(e)
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            if attempt >= max_retries - 1:
                return result
    
    return result

def download_company_reports(cid, company_name, ir_url, years=None, output_dir='companies'):
    """
    Download annual reports for a company.
    
    Args:
        cid: Company identifier (e.g., 'C1')
        company_name: Company name for logging
        ir_url: Investor relations URL
        years: List of years to download (default: 2019-2024)
        output_dir: Base directory for downloads
    
    Returns:
        dict: Summary of downloads
        
    Raises:
        DownloadError: If repeated fetch failures occur
    """
    if years is None:
        years = list(range(2019, 2025))
    
    print(f"\n{'='*60}")
    print(f"Processing: {company_name} ({cid})")
    print(f"IR URL: {ir_url}")
    print(f"{'='*60}")
    
    # Find reports (may raise DownloadError)
    # Pass company_name to enable MFN fallback
    reports = find_annual_reports(ir_url, years, company_name=company_name)
    
    if not reports:
        print("⚠ No annual reports found")
        return {
            'cid': cid,
            'company': company_name,
            'found': 0,
            'downloaded': 0,
            'failed': 0,
            'downloads': []
        }
    
    # Download each report
    company_dir = os.path.join(output_dir, cid)
    downloads = []
    
    # Group reports by year to handle multiple candidates
    reports_by_year = {}
    for report in reports:
        year = report['year']
        if year not in reports_by_year:
            reports_by_year[year] = []
        reports_by_year[year].append(report)
    
    for year in sorted(reports_by_year.keys(), reverse=True):
        candidates = reports_by_year[year]
        output_path = os.path.join(company_dir, f"annual_report_{year}.pdf")
        
        # Skip if already exists
        if os.path.exists(output_path):
            print(f"⊙ {year}: Already exists, skipping")
            downloads.append({
                'year': year,
                'status': 'skipped',
                'reason': 'already_exists'
            })
            continue
        
        # Try each candidate until we get a valid one
        downloaded = False
        for idx, report in enumerate(candidates):
            url = report['url']
            title = report.get('title', 'Unknown title')
            
            if len(candidates) > 1:
                print(f"\n  [{year}] Trying candidate {idx+1}/{len(candidates)}")
                print(f"      Title: {title[:70]}")
                print(f"      URL: {url}")
            else:
                print(f"\n  [{year}] Downloading single candidate")
                print(f"      Title: {title[:70]}")
                print(f"      URL: {url}")
            
            # Download with built-in retry and user agent rotation, pass year hint
            result = download_pdf(url, output_path, year_hint=year)
            
            if result['success']:
                print(f"      ✓ Downloaded: {result['pages']} pages, {result['size_mb']:.1f} MB")
                
                # Quick validation: check if it's reasonable
                is_valid = True
                validation_issues = []
                
                # Already checked pages in download_pdf, but double-check other criteria
                if result['pages'] > 500:
                    is_valid = False
                    validation_issues.append(f"Too many pages ({result['pages']})")
                
                if is_valid:
                    print(f"      ✓ Validation passed - this is a valid annual report")
                    downloads.append({
                        'year': year,
                        'status': 'success',
                        'url': url,
                        'pages': result['pages'],
                        'size_mb': result['size_mb'],
                        'path': output_path,
                        'timestamp': datetime.now().isoformat()
                    })
                    downloaded = True
                    break
                else:
                    print(f"      ✗ Validation failed: {', '.join(validation_issues)}")
                    print(f"      → Removing invalid file and trying next candidate...")
                    # Remove invalid file and try next candidate
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    if idx < len(candidates) - 1:
                        continue
            else:
                print(f"      ✗ Download failed: {result['error']}")
                if idx < len(candidates) - 1:
                    print(f"      → Trying next candidate...")
                    continue
        
        if not downloaded:
            print(f"\n  ✗ [{year}] All {len(candidates)} candidate(s) failed - no valid report downloaded")
            downloads.append({
                'year': year,
                'status': 'failed',
                'url': candidates[0]['url'] if candidates else None,
                'error': result['error']
            })
        
        # Be nice to servers
        time.sleep(1)
    
    # Summary
    print("\n" + "="*70)
    print("DOWNLOAD SUMMARY")
    print("="*70)
    
    successful = sum(1 for d in downloads if d['status'] == 'success')
    failed = sum(1 for d in downloads if d['status'] == 'failed')
    skipped = sum(1 for d in downloads if d['status'] == 'skipped')
    
    print(f"Total: {len(downloads)} reports")
    print(f"  ✓ Success: {successful}")
    print(f"  ⊙ Skipped (already exists): {skipped}")
    print(f"  ✗ Failed: {failed}")
    
    if failed > 0:
        print("\nFailed reports:")
        for d in downloads:
            if d['status'] == 'failed':
                print(f"  - Year {d['year']}: {d.get('error', 'Unknown error')}")
    skipped = sum(1 for d in downloads if d['status'] == 'skipped')
    
    print(f"\nSummary: {successful} downloaded, {skipped} skipped, {failed} failed")
    
    return {
        'cid': cid,
        'company': company_name,
        'found': len(reports),
        'downloaded': successful,
        'skipped': skipped,
        'failed': failed,
        'downloads': downloads
    }
