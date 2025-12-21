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
            print(f"{'  ' * depth}  → Found {len(links)} links to analyze")
            
            # Patterns to identify annual reports (more flexible - allow words in between)
            annual_patterns = [
                r'annual.*report',
                r'årsredovisning',
                r'årsbericht',
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
                
                if is_pdf_link:
                    pdf_count += 1
                
                # Check if this matches annual report pattern AND doesn't match exclusion pattern
                matches_annual = re.search(pattern, combined, re.IGNORECASE)
                matches_exclude = re.search(exclude_pattern, combined, re.IGNORECASE)
                
                if is_pdf_link and matches_annual:
                    if matches_exclude:
                        excluded_count += 1
                        # Uncomment for even more detail:
                        # print(f"{'  ' * depth}    ✗ Excluded: {text[:50]} (quarterly/SEC filing)")
                        continue
                    
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
                                print(f"{'  ' * depth}    ✓ Found report: {year} - {text[:60]}")
                                results.append({
                                    'year': year,
                                    'url': abs_url,
                                    'title': link.get_text(strip=True),
                                    'source_page': url
                                })
                
                # If depth allows, check for navigation links to follow
                if depth < max_depth and re.search(nav_pattern, combined, re.IGNORECASE):
                    # Make absolute URL
                    abs_url = urljoin(url, href)
                    
                    # Allow following links on same domain or subdomains (e.g., global.abb.com -> library.e.abb.com)
                    link_netloc = urlparse(abs_url).netloc
                    if base_domain in link_netloc:
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
            resp = requests.get(actual_pdf_url, timeout=30, headers=headers, stream=True)
            
            if resp.status_code != 200:
                result['error'] = f"HTTP {resp.status_code}"
                print(f"  ✗ HTTP error {resp.status_code}")
                if attempt < max_retries - 1:
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
            candidate_label = f"candidate {idx+1}/{len(candidates)}" if len(candidates) > 1 else ""
            
            if candidate_label:
                print(f"  Trying {year} {candidate_label}: {report.get('title', '')[:50]}")
            
            # Download with built-in retry and user agent rotation, pass year hint
            result = download_pdf(url, output_path, year_hint=year)
            
            if result['success']:
                # Quick validation: check if it's reasonable
                is_valid = True
                validation_issues = []
                
                # Already checked pages in download_pdf, but double-check other criteria
                if result['pages'] > 500:
                    is_valid = False
                    validation_issues.append(f"Too many pages ({result['pages']})")
                
                if is_valid:
                    print(f"  ✓ Valid report for {year}")
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
                    print(f"  ✗ Downloaded but invalid: {', '.join(validation_issues)}")
                    # Remove invalid file and try next candidate
                    if os.path.exists(output_path):
                        os.remove(output_path)
            else:
                print(f"  ✗ Download failed: {result['error']}")
        
        if not downloaded:
            print(f"✗ {year}: All candidates failed")
            downloads.append({
                'year': year,
                'status': 'failed',
                'url': candidates[0]['url'] if candidates else None,
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
