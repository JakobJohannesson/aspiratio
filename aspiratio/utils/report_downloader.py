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

def find_annual_reports(ir_url, years=None, max_depth=2, max_failures=3):
    """
    Search IR page for annual report PDFs.
    
    Args:
        ir_url: Investor relations page URL
        years: List of years to find (default: 2019-2024)
        max_depth: How many levels deep to search (default: 2)
        max_failures: Max consecutive failures before raising error (default: 3)
    
    Returns:
        List of dicts: [{'year': 2024, 'url': 'https://...', 'title': '...'}]
    
    Raises:
        DownloadError: If max_failures consecutive errors occur
    """
    if years is None:
        years = list(range(2019, 2025))
    
    results = []
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
            resp = requests.get(url_no_fragment, timeout=10, headers=headers)
            
            if resp.status_code != 200:
                consecutive_failures += 1
                print(f"{'  ' * depth}HTTP {resp.status_code} (failure {consecutive_failures}/{max_failures})")
                if consecutive_failures >= max_failures:
                    raise DownloadError(f"Failed to fetch {max_failures} pages in a row (last: HTTP {resp.status_code})")
                return
            
            # Reset failure counter on success
            consecutive_failures = 0
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Find all links on the page
            links = soup.find_all('a', href=True)
            
            # Patterns to identify annual reports (more flexible - allow words in between)
            annual_patterns = [
                r'annual.*report',
                r'årsredovisning',
                r'årsbericht',
                r'rapport.*annuel',
                r'financial.*report',
                r'integrated.*report',
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
            nav_pattern = '|'.join(navigation_patterns)
            
            pages_to_visit = []
            
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                title = link.get('title', '').lower()
                
                # Combine text sources
                combined = f"{href} {text} {title}".lower()
                
                # Check if it's a PDF link for annual reports
                # Either URL ends with .pdf OR text mentions (PDF) OR href contains 'download' or 'pdf'
                is_pdf_link = (
                    href.lower().endswith('.pdf') or
                    '(pdf)' in text or
                    'pdf' in href.lower() or
                    'download' in href.lower()
                )
                
                if is_pdf_link and re.search(pattern, combined, re.IGNORECASE):
                    # Make absolute URL
                    abs_url = urljoin(url, href)
                    
                    # Try to extract year from URL or text
                    # Support formats: 2024, 24, 24-25, 2024-25, 2024/25
                    year_match = re.search(r'(?:20)?(?:19|20|21|22|23|24)(?:[/-](?:20)?(?:20|21|22|23|24|25))?', combined)
                    if year_match:
                        # Extract the first year mentioned
                        year_str = year_match.group(0)
                        # Parse just the first year (e.g., "24-25" -> 24 -> 2024)
                        first_year = re.search(r'(?:20)?(19|20|21|22|23|24)', year_str)
                        if first_year:
                            year_num = int(first_year.group(1))
                            # Convert short year to full year (24 -> 2024)
                            year = 2000 + year_num if year_num > 10 else 2000 + year_num
                            
                            if year in years:
                                results.append({
                                    'year': year,
                                    'url': abs_url,
                                    'title': link.get_text(strip=True),
                                    'source_page': url
                                })
                
                # If depth allows, check for navigation links to follow
                elif depth < max_depth and re.search(nav_pattern, combined, re.IGNORECASE):
                    # Make absolute URL
                    abs_url = urljoin(url, href)
                    
                    # Allow following links on same domain or subdomains (e.g., global.abb.com -> library.e.abb.com)
                    link_netloc = urlparse(abs_url).netloc
                    if base_domain in link_netloc:
                        pages_to_visit.append(abs_url)
            
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
            '/annual-reports',
            '/annual-reporting-suite',
            '/reports-and-publications',
            '/financial-reports/annual-reports',
        ]
        
        for path in common_paths:
            test_url = f"{parsed.scheme}://{parsed.netloc}{path}"
            if test_url not in visited:
                search_page(test_url, 0)
                if results:  # If we found something, stop trying
                    break
    
    # Deduplicate by year (keep first occurrence)
    seen_years = set()
    unique_results = []
    for r in results:
        if r['year'] not in seen_years:
            seen_years.add(r['year'])
            unique_results.append(r)
    
    print(f"Found {len(unique_results)} annual reports")
    return sorted(unique_results, key=lambda x: x['year'], reverse=True)

def download_pdf(url, output_path, min_pages=10, max_retries=3):
    """
    Download PDF and validate it meets minimum page requirement.
    
    Args:
        url: PDF URL
        output_path: Where to save the file
        min_pages: Minimum number of pages required (default 10)
        max_retries: Maximum download attempts with user agent rotation (default 3)
    
    Returns:
        dict: {'success': bool, 'pages': int, 'size_mb': float, 'error': str}
    """
    result = {
        'success': False,
        'pages': 0,
        'size_mb': 0.0,
        'error': None
    }
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f"  Retry {attempt}/{max_retries}...")
                time.sleep(2)  # Wait before retry
            
            print(f"Downloading {url}...")
            headers = {"User-Agent": get_random_user_agent()}
            resp = requests.get(url, timeout=30, headers=headers, stream=True)
            
            if resp.status_code != 200:
                result['error'] = f"HTTP {resp.status_code}"
                if attempt < max_retries - 1:
                    continue  # Try again with different user agent
                return result
        
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Download to temporary file first
            temp_path = output_path + '.tmp'
            with open(temp_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Get file size
            size_bytes = os.path.getsize(temp_path)
            result['size_mb'] = size_bytes / (1024 * 1024)
            
            # Validate it's a valid PDF with minimum pages
            try:
                with open(temp_path, 'rb') as f:
                    pdf = PdfReader(f)
                    result['pages'] = len(pdf.pages)
            except Exception as e:
                result['error'] = f"PDF validation failed: {e}"
                os.remove(temp_path)
                if attempt < max_retries - 1:
                    continue  # Try again
                return result
            
            # Check minimum pages
            if result['pages'] < min_pages:
                result['error'] = f"Only {result['pages']} pages (min {min_pages} required)"
                os.remove(temp_path)
                return result
            
            # Move temp file to final location
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rename(temp_path, output_path)
            
            result['success'] = True
            print(f"✓ Downloaded: {result['pages']} pages, {result['size_mb']:.1f} MB")
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
    reports = find_annual_reports(ir_url, years)
    
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
    
    for report in reports:
        year = report['year']
        url = report['url']
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
        
        # Download with built-in retry and user agent rotation
        result = download_pdf(url, output_path)
        
        if result['success']:
            downloads.append({
                'year': year,
                'status': 'success',
                'url': url,
                'pages': result['pages'],
                'size_mb': result['size_mb'],
                'path': output_path,
                'timestamp': datetime.now().isoformat()
            })
        else:
            print(f"✗ {year}: Failed - {result['error']}")
            downloads.append({
                'year': year,
                'status': 'failed',
                'url': url,
                'error': result['error']
            })
        
        # Be nice to servers
        time.sleep(1)
    
    # Summary
    successful = sum(1 for d in downloads if d['status'] == 'success')
    failed = sum(1 for d in downloads if d['status'] == 'failed')
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
