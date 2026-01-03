"""
Wget-based search for MFN and Cision sources.

This module uses wget to mirror company pages from mfn.se and news.cision.com,
storing the HTML persistently in the companies folder for later processing.

The stored HTML can be used for:
- Annual reports
- Quarterly reports (future)
- Press releases (future)
"""
import os
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import quote
from bs4 import BeautifulSoup


def normalize_company_name(company_name):
    """
    Normalize company name for URL construction.
    
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


def get_company_mirror_dir(company_id, source):
    """
    Get the directory path for storing mirrored content.
    
    Args:
        company_id: Company ID (e.g., "S1")
        source: Source name ("mfn" or "cision")
    
    Returns:
        Path to the mirror directory
    """
    base_dir = Path("companies") / company_id / f"mirror_{source}"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def wget_mirror_site(url, output_dir, max_depth=2):
    """
    Use wget to mirror a website for offline processing.
    
    Args:
        url: URL to mirror
        output_dir: Directory to store mirrored content
        max_depth: Maximum recursion depth for wget (default: 2)
    
    Returns:
        True if successful, False otherwise
    """
    # wget flags explained:
    # -r: recursive download
    # -E: adjust extensions (.html, .css, etc.)
    # -k: convert links for local viewing
    # -p: download page requisites (images, css, etc.)
    # -np: don't ascend to parent directory
    # -nc: no clobber (don't download existing files)
    # --random-wait: random wait between requests (0.5-1.5 * wait time)
    # -l: maximum recursion depth
    # -P: prefix (output directory)
    # --user-agent: identify as a browser
    
    cmd = [
        'wget',
        '-r',  # recursive
        '-E',  # adjust extensions
        '-k',  # convert links
        '-p',  # page requisites
        '-np',  # no parent
        '-nc',  # no clobber
        '--random-wait',  # random delays
        '-l', str(max_depth),  # max depth
        '-P', str(output_dir),  # output directory
        '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        '--timeout=30',  # connection timeout
        '--tries=3',  # retry attempts
        '--wait=1',  # wait 1 second between requests (with random-wait, becomes 0.5-1.5s)
        url
    ]
    
    try:
        print(f"  📥 Mirroring {url} to {output_dir}")
        print(f"     Command: wget with recursive download (depth={max_depth})")
        
        # Run wget
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0 or result.returncode == 8:
            # returncode 8 means some files downloaded, some not found (acceptable)
            print(f"    ✓ Successfully mirrored site")
            return True
        else:
            print(f"    ✗ wget failed with code {result.returncode}")
            if result.stderr:
                print(f"    Error: {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"    ✗ wget timed out after 5 minutes")
        return False
    except FileNotFoundError:
        print(f"    ✗ wget command not found - please install wget")
        return False
    except Exception as e:
        print(f"    ✗ Error running wget: {e}")
        return False


def mirror_mfn_company(company_name, company_id):
    """
    Mirror MFN company page using wget.
    
    Args:
        company_name: Company name (e.g., "Hexagon AB")
        company_id: Company ID (e.g., "S1")
    
    Returns:
        Path to mirrored content if successful, None otherwise
    """
    normalized_name = normalize_company_name(company_name)
    url = f"https://mfn.se/all/a/{normalized_name}"
    
    mirror_dir = get_company_mirror_dir(company_id, "mfn")
    
    print(f"  🌐 Mirroring MFN for {company_name} ({company_id})")
    
    if wget_mirror_site(url, mirror_dir, max_depth=2):
        return mirror_dir
    else:
        # Try alternative URL pattern
        alt_url = f"https://mfn.se/all/{normalized_name}"
        print(f"  🔄 Trying alternative URL: {alt_url}")
        if wget_mirror_site(alt_url, mirror_dir, max_depth=2):
            return mirror_dir
    
    return None


def mirror_cision_company(company_name, company_id):
    """
    Mirror Cision company page using wget.
    
    Args:
        company_name: Company name (e.g., "Hexagon AB")
        company_id: Company ID (e.g., "S1")
    
    Returns:
        Path to mirrored content if successful, None otherwise
    """
    normalized_name = normalize_company_name(company_name)
    
    # Try the financial page pattern
    url = f"https://news.cision.com/{normalized_name}/?m=Financial"
    
    mirror_dir = get_company_mirror_dir(company_id, "cision")
    
    print(f"  🌐 Mirroring Cision for {company_name} ({company_id})")
    
    if wget_mirror_site(url, mirror_dir, max_depth=2):
        return mirror_dir
    else:
        # Try search query pattern
        search_url = f"https://news.cision.com/?q={quote(normalized_name)}"
        print(f"  🔄 Trying search URL: {search_url}")
        if wget_mirror_site(search_url, mirror_dir, max_depth=2):
            return mirror_dir
    
    return None


def parse_mirrored_mfn_for_reports(mirror_dir, company_name, years):
    """
    Parse mirrored MFN HTML to find annual reports.
    
    Args:
        mirror_dir: Path to mirrored content
        company_name: Company name for filtering
        years: List of years to search for
    
    Returns:
        List of dicts: [{'year': 2020, 'url': 'https://...', 'title': '...', 'source': 'mfn'}]
    """
    results = []
    
    if not mirror_dir or not os.path.exists(mirror_dir):
        return results
    
    print(f"  📖 Parsing mirrored MFN content from {mirror_dir}")
    
    # Find all HTML files in the mirror
    html_files = list(Path(mirror_dir).rglob("*.html"))
    
    for html_file in html_files:
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                
            # Look for links to Cision PDFs and report pages
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                # Check for Cision PDF links or report pages
                if 'cision.com' in href and '.pdf' in href.lower():
                    # Extract year from link or text
                    for year in years:
                        if str(year) in href or str(year) in text:
                            results.append({
                                'year': year,
                                'url': href,
                                'title': f'Annual Report {year} (MFN/Cision)',
                                'source': 'mfn_wget',
                                'local_file': str(html_file)
                            })
                            break
                            
        except Exception as e:
            print(f"    ⚠ Error parsing {html_file}: {e}")
            continue
    
    print(f"    ✓ Found {len(results)} potential reports in mirrored content")
    return results


def parse_mirrored_cision_for_reports(mirror_dir, company_name, years):
    """
    Parse mirrored Cision HTML to find annual reports.
    
    Args:
        mirror_dir: Path to mirrored content
        company_name: Company name for filtering
        years: List of years to search for
    
    Returns:
        List of dicts: [{'year': 2020, 'url': 'https://...', 'title': '...', 'source': 'cision'}]
    """
    results = []
    
    if not mirror_dir or not os.path.exists(mirror_dir):
        return results
    
    print(f"  📖 Parsing mirrored Cision content from {mirror_dir}")
    
    # Find all HTML files in the mirror
    html_files = list(Path(mirror_dir).rglob("*.html"))
    
    for html_file in html_files:
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                
            # Look for press releases with annual reports
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                combined = f"{href} {text}".lower()
                
                # Check for annual report keywords
                is_annual = any(kw in combined for kw in [
                    'annual report', 'year-end report', 'årsredovisning',
                    'full year', 'full-year'
                ])
                
                # Exclude quarterly
                is_quarterly = any(kw in combined for kw in [
                    'q1', 'q2', 'q3', 'q4', 'quarter', 'interim', 'kvartals'
                ])
                
                if is_annual and not is_quarterly:
                    # Check for year and PDF
                    for year in years:
                        if str(year) in combined:
                            if '.pdf' in href.lower() or 'cision.com' in href:
                                results.append({
                                    'year': year,
                                    'url': href,
                                    'title': f'Annual Report {year} (Cision)',
                                    'source': 'cision_wget',
                                    'local_file': str(html_file)
                                })
                                break
                                
        except Exception as e:
            print(f"    ⚠ Error parsing {html_file}: {e}")
            continue
    
    print(f"    ✓ Found {len(results)} potential reports in mirrored content")
    return results


def find_reports_via_wget(company_name, company_id, years, source='both'):
    """
    Find annual reports using wget mirroring for MFN and/or Cision.
    
    This function mirrors the company pages locally and then parses the HTML
    to find annual reports. The mirrored content is kept for future use.
    
    Args:
        company_name: Company name (e.g., "Hexagon AB")
        company_id: Company ID (e.g., "S1")
        years: List of years to search for
        source: Which source to use ('mfn', 'cision', or 'both')
    
    Returns:
        List of dicts: [{'year': 2020, 'url': 'https://...', 'title': '...', 'source': '...'}]
    """
    results = []
    
    print(f"  📡 Using wget to mirror and search for {company_name} ({company_id})")
    
    # Mirror and parse MFN
    if source in ['mfn', 'both']:
        mfn_mirror = mirror_mfn_company(company_name, company_id)
        if mfn_mirror:
            mfn_results = parse_mirrored_mfn_for_reports(mfn_mirror, company_name, years)
            results.extend(mfn_results)
    
    # Mirror and parse Cision
    if source in ['cision', 'both']:
        cision_mirror = mirror_cision_company(company_name, company_id)
        if cision_mirror:
            cision_results = parse_mirrored_cision_for_reports(cision_mirror, company_name, years)
            results.extend(cision_results)
    
    # Deduplicate by year
    seen_years = set()
    unique_results = []
    for r in results:
        if r['year'] not in seen_years:
            seen_years.add(r['year'])
            unique_results.append(r)
    
    print(f"  ✓ Found {len(unique_results)} unique reports via wget mirroring")
    return unique_results


if __name__ == "__main__":
    # Test with Hexagon
    print("="*80)
    print("Testing wget mirroring with Hexagon")
    print("="*80)
    
    results = find_reports_via_wget("Hexagon AB", "TEST", [2020, 2021], source='both')
    
    if results:
        print(f"\n✓ SUCCESS: Found {len(results)} reports")
        for r in results:
            print(f"  Year: {r['year']}")
            print(f"  URL: {r['url']}")
            print(f"  Source: {r['source']}")
            print()
    else:
        print("\n✗ No reports found")
