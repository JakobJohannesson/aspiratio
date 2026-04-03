#!/usr/bin/env python3
"""Initialize manifest.json from existing validated reports on disk.

Run this once to migrate from filesystem-based tracking to the transactional model.
Scans companies_validated/ and creates 'complete' transactions for every valid PDF found.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from aspiratio.downloader import (
    init_manifest,
    load_manifest,
    load_sources,
    save_manifest,
    sha256_file,
    verify_pdf,
)


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(__name__)

    sources_path = "report_sources.yaml"
    manifest_path = "manifest.json"
    reports_dir = Path("companies_validated")

    # Create pending transactions for all company-years
    manifest = init_manifest(sources_path, manifest_path)
    sources = load_sources(sources_path)
    txs = manifest["transactions"]

    # Build CID→company lookup
    companies = {c["cid"]: c for c in sources["companies"]}

    migrated = 0
    for tx_id, tx in txs.items():
        if tx["status"] == "complete":
            continue

        cid = tx["cid"]
        year = str(tx["year"])
        company_dir = reports_dir / cid

        if not company_dir.exists():
            continue

        # Find any PDF with the year in the name
        for pdf in company_dir.glob("*.pdf"):
            if year not in pdf.name:
                continue

            ok, pages, size_mb, err = verify_pdf(pdf)
            if not ok:
                logger.warning(f"  {tx_id}: {pdf.name} failed verification: {err}")
                continue

            tx["status"] = "complete"
            tx["filename"] = str(pdf.relative_to(reports_dir.parent))
            tx["pages"] = pages
            tx["size_mb"] = size_mb
            tx["sha256"] = sha256_file(pdf)
            tx["verified_at"] = manifest["meta"].get("updated_at", "")
            tx["source"] = "migrated"
            migrated += 1
            logger.info(f"  {tx_id}: {pdf.name} ({pages}p, {size_mb}MB)")
            break

    save_manifest(manifest, manifest_path)

    total = len(txs)
    complete = sum(1 for t in txs.values() if t["status"] == "complete")
    pending = sum(1 for t in txs.values() if t["status"] == "pending")

    print(f"\nMigrated {migrated} existing reports")
    print(f"Manifest: {complete}/{total} complete, {pending} pending")


if __name__ == "__main__":
    main()
