"""
Transactional annual report downloader.

Each report is a transaction in manifest.json:
  PENDING → DOWNLOADED → COMPLETE
              ↘ FAILED

manifest.json is the single source of truth for the project.
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
import yaml
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

ANNUAL_KEYWORDS = [
    "annual report", "annual-report", "annualreport", "annual_report",
    "årsredovisning", "arsredovisning", "ars-redovisning",
]

EXCLUDE_KEYWORDS = [
    "quarterly", "quarter", "interim", "q1-", "q2-", "q3-", "q4-",
    "/q1", "/q2", "/q3", "/q4",
    "delars", "kvartals", "halvår", "half-year", "halfyear",
    "sustainability", "hallbarhet", "hållbarhet",
    "corporate-governance", "bolagsstyrning",
    "form-20-f", "form_20-f", "20-f",
    "remuneration", "ersattning",
    "proxy", "notice-of-agm",
]

SUBPAGE_KEYWORDS = [
    "annual-report", "annual_report", "annualreport", "annual-reports",
    "reports", "financial-reports", "publications",
    "arsredovisning", "årsredovisning",
    "reports-and-presentations", "financial-information",
    "reporting", "report-archive",
]


# ---------------------------------------------------------------------------
# Manifest operations
# ---------------------------------------------------------------------------

def load_manifest(path="manifest.json"):
    path = Path(path)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"meta": {}, "transactions": {}}


def save_manifest(manifest, path="manifest.json"):
    manifest["meta"]["updated_at"] = datetime.now(timezone.utc).isoformat()
    tmp = Path(path).with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def init_manifest(sources_path="report_sources.yaml", manifest_path="manifest.json"):
    """Create pending transactions for every company-year not already in the manifest."""
    sources = load_sources(sources_path)
    manifest = load_manifest(manifest_path)
    years = sources["target_years"]
    companies = sources["companies"]

    manifest["meta"]["target_years"] = years
    manifest["meta"]["companies_count"] = len(companies)

    added = 0
    for company in companies:
        for year in years:
            tx_id = f"{company['cid']}_{year}"
            if tx_id not in manifest["transactions"]:
                manifest["transactions"][tx_id] = {
                    "cid": company["cid"],
                    "company": company["name"],
                    "year": year,
                    "status": "pending",
                }
                added += 1

    save_manifest(manifest, manifest_path)
    logger.info(f"Manifest: {added} new pending transactions ({len(manifest['transactions'])} total)")
    return manifest


# ---------------------------------------------------------------------------
# Web scraping helpers (unchanged)
# ---------------------------------------------------------------------------

def load_sources(path="report_sources.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def fetch_page(url, timeout=30):
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    resp.raise_for_status()
    return resp.text


def extract_links(html, base_url):
    soup = BeautifulSoup(html, "lxml")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
        links.append({"url": urljoin(base_url, href), "text": a.get_text(strip=True)})
    return links


def score_annual_report(link, year, company_name, aliases=None):
    url = link["url"].lower()
    text = link["text"].lower()
    combined = f"{url} {text}"
    year_str = str(year)

    fy_variants = [
        year_str,
        f"{year}/{str(year + 1)[-2:]}",
        f"{year}-{str(year + 1)[-2:]}",
        f"{year - 1}/{str(year)[-2:]}",
        f"{year - 1}-{str(year)[-2:]}",
    ]
    if not any(v in combined for v in fy_variants):
        return -100

    score = 10
    if any(kw in combined for kw in ANNUAL_KEYWORDS):
        score += 20
    if any(kw in combined for kw in EXCLUDE_KEYWORDS):
        return -50
    if url.lower().endswith(".pdf"):
        score += 10
    else:
        score -= 15
    names = [company_name.lower().split()[0]]
    if aliases:
        names.extend(a.lower() for a in aliases)
    if any(n in combined for n in names):
        score += 5
    if "english" in combined or "/en/" in url:
        score += 3
    return score


def find_subpages(links, base_url):
    base_domain = urlparse(base_url).netloc
    subpages = set()
    for link in links:
        url = link["url"]
        if urlparse(url).netloc != base_domain:
            continue
        if url.lower().endswith(".pdf"):
            continue
        combined = f"{link['url'].lower()} {link['text'].lower()}"
        if any(kw in combined for kw in SUBPAGE_KEYWORDS):
            subpages.add(url)
    return list(subpages)[:8]


def find_annual_report_url(ir_url, company_name, year, aliases=None):
    """Find the best annual report PDF URL. Returns (url, score) or (None, 0)."""
    try:
        html = fetch_page(ir_url)
    except Exception as e:
        logger.warning(f"  Failed to fetch {ir_url}: {e}")
        return None, 0

    all_links = extract_links(html, ir_url)
    candidates = []

    for link in all_links:
        if link["url"].lower().endswith(".pdf"):
            s = score_annual_report(link, year, company_name, aliases)
            if s > 0:
                candidates.append((s, link["url"], link["text"]))

    if not candidates or max(c[0] for c in candidates) < 25:
        for sp_url in find_subpages(all_links, ir_url):
            try:
                sp_html = fetch_page(sp_url)
                for link in extract_links(sp_html, sp_url):
                    if link["url"].lower().endswith(".pdf"):
                        s = score_annual_report(link, year, company_name, aliases)
                        if s > 0:
                            candidates.append((s, link["url"], link["text"]))
            except Exception:
                continue
            time.sleep(0.5)

    if not candidates:
        return None, 0
    candidates.sort(reverse=True)
    return candidates[0][1], candidates[0][0]


# ---------------------------------------------------------------------------
# Download & validate
# ---------------------------------------------------------------------------

def download_pdf(url, output_path, timeout=60):
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, headers=headers, timeout=timeout, stream=True)
    resp.raise_for_status()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return output_path


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_pdf(pdf_path, min_pages=30, max_pages=600, min_size_kb=500):
    """Verify a PDF is a plausible annual report.

    Returns (ok, pages, size_mb, error_msg).
    """
    path = Path(pdf_path)
    if not path.exists():
        return False, 0, 0, "file missing"

    size_mb = round(path.stat().st_size / (1024 * 1024), 1)
    if path.stat().st_size < min_size_kb * 1024:
        return False, 0, size_mb, f"too small ({size_mb}MB)"

    with open(path, "rb") as f:
        if f.read(5) != b"%PDF-":
            return False, 0, size_mb, "not a PDF"

    try:
        pages = len(PdfReader(str(path)).pages)
    except Exception as e:
        return False, 0, size_mb, f"unreadable PDF: {e}"

    if pages < min_pages:
        return False, pages, size_mb, f"too few pages ({pages})"
    if pages > max_pages:
        return False, pages, size_mb, f"too many pages ({pages})"

    return True, pages, size_mb, None


# ---------------------------------------------------------------------------
# Transaction processing
# ---------------------------------------------------------------------------

def _lookup_company(sources, cid):
    for c in sources["companies"]:
        if c["cid"] == cid:
            return c
    return None


def process_transaction(tx_id, tx, sources, reports_dir):
    """Process a single transaction through its lifecycle.

    Mutates tx in-place and returns the updated status.
    """
    now = datetime.now(timezone.utc).isoformat()
    cid = tx["cid"]
    year = tx["year"]
    company = _lookup_company(sources, cid)
    if not company:
        tx["status"] = "failed"
        tx["error"] = f"company {cid} not in sources"
        return tx["status"]

    name = company["name"]
    ir_url = company["ir_url"]
    aliases = company.get("aliases", [])
    direct_urls = company.get("direct_urls", {})
    filepath = Path(reports_dir) / cid / f"{cid}_{year}_annual_report.pdf"

    # --- Step 1: Download ---------------------------------------------------
    if tx["status"] == "pending":
        # Check if file already exists on disk (e.g. from previous run)
        alt = Path(reports_dir) / cid / f"{cid}_{year}_Annual_Report.pdf"
        for existing in [filepath, alt]:
            if existing.exists():
                tx["filename"] = str(existing.relative_to(Path(reports_dir).parent))
                tx["status"] = "downloaded"
                tx["downloaded_at"] = now
                logger.info(f"  [{tx_id}] Found existing file")
                break

        if tx["status"] == "pending":
            # Try direct URL first, then IR page search
            pdf_url = direct_urls.get(str(year))
            if not pdf_url:
                pdf_url, _ = find_annual_report_url(ir_url, name, year, aliases)

            if not pdf_url:
                tx["status"] = "failed"
                tx["error"] = "no report URL found"
                tx["failed_at"] = now
                return tx["status"]

            try:
                download_pdf(pdf_url, filepath)
            except Exception as e:
                tx["status"] = "failed"
                tx["error"] = f"download error: {e}"
                tx["failed_at"] = now
                return tx["status"]

            tx["source_url"] = pdf_url
            tx["filename"] = str(filepath.relative_to(Path(reports_dir).parent))
            tx["status"] = "downloaded"
            tx["downloaded_at"] = now
            logger.info(f"  [{tx_id}] Downloaded")

    # --- Step 2: Verify -----------------------------------------------------
    if tx["status"] == "downloaded":
        # Resolve actual file path
        actual_path = Path(reports_dir).parent / tx["filename"] if "filename" in tx else filepath
        ok, pages, size_mb, err = verify_pdf(actual_path)

        if not ok:
            tx["status"] = "failed"
            tx["error"] = f"verification: {err}"
            tx["failed_at"] = now
            # Remove bad file
            actual_path.unlink(missing_ok=True)
            return tx["status"]

        tx["pages"] = pages
        tx["size_mb"] = size_mb
        tx["sha256"] = sha256_file(actual_path)
        tx["status"] = "complete"
        tx["verified_at"] = now
        logger.info(f"  [{tx_id}] Complete ({pages}p, {size_mb}MB)")

    return tx["status"]


def run(sources_path="report_sources.yaml", manifest_path="manifest.json",
        reports_dir="companies_validated", company_filter=None):
    """Process all non-complete transactions.

    Returns (completed, failed, skipped) counts.
    """
    sources = load_sources(sources_path)
    manifest = load_manifest(manifest_path)
    txs = manifest["transactions"]

    # Mark session as live
    manifest["meta"]["live"] = True
    manifest["meta"]["current_tx"] = None
    save_manifest(manifest, manifest_path)

    completed = failed = skipped = 0

    try:
        for tx_id, tx in sorted(txs.items()):
            if tx["status"] == "complete":
                skipped += 1
                continue

            if company_filter and tx["cid"] != company_filter:
                skipped += 1
                continue

            # Broadcast which transaction is active
            manifest["meta"]["current_tx"] = tx_id
            save_manifest(manifest, manifest_path)

            logger.info(f"\n--- {tx_id}: {tx['company']} {tx['year']} [{tx['status']}]")
            result = process_transaction(tx_id, tx, sources, reports_dir)

            if result == "complete":
                completed += 1
            elif result == "failed":
                failed += 1

            # Save after each transaction (crash-safe)
            manifest["meta"]["current_tx"] = None
            save_manifest(manifest, manifest_path)
            time.sleep(1)
    finally:
        # Always clear live state on exit
        manifest["meta"]["live"] = False
        manifest["meta"]["current_tx"] = None
        save_manifest(manifest, manifest_path)

    return completed, failed, skipped
