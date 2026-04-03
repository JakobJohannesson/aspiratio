#!/usr/bin/env python3
"""Process pending transactions: download, verify, and complete annual reports.

Starts a live API server on port 8787 so the dashboard can poll manifest.json
in real-time while downloads are running.
"""

import argparse
import logging
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from aspiratio.downloader import init_manifest, load_manifest, run

_manifest_path = "manifest.json"


def _set_manifest_path(path):
    global _manifest_path
    _manifest_path = path


# ---------------------------------------------------------------------------
# Live API server — serves manifest.json with CORS for dashboard polling
# ---------------------------------------------------------------------------

class ManifestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/manifest.json":
            try:
                with open(_manifest_path, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-cache, no-store")
                self.end_headers()
                self.wfile.write(data)
            except FileNotFoundError:
                self.send_error(404)
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress request logging


def start_live_server(port=8787):
    server = HTTPServer(("0.0.0.0", port), ManifestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Process annual report transactions")
    parser.add_argument("--sources", default="report_sources.yaml")
    parser.add_argument("--manifest", default="manifest.json")
    parser.add_argument("--reports-dir", default="companies_validated")
    parser.add_argument("--company", help="Only process specific CID (e.g. S1)")
    parser.add_argument("--no-serve", action="store_true", help="Don't start live API server")
    parser.add_argument("--port", type=int, default=8787, help="Live server port")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    _set_manifest_path(args.manifest)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )

    # Start live server
    server = None
    if not args.no_serve:
        server = start_live_server(args.port)
        print(f"Live API: http://localhost:{args.port}/manifest.json")
        print(f"Dashboard: cd dashboard && npm run dev")
        print()

    # Ensure all company-years have transactions
    init_manifest(args.sources, args.manifest)

    # Process pending transactions
    completed, failed, skipped = run(
        sources_path=args.sources,
        manifest_path=args.manifest,
        reports_dir=args.reports_dir,
        company_filter=args.company,
    )

    # Summary
    manifest = load_manifest(args.manifest)
    txs = manifest["transactions"]
    total = len(txs)
    total_complete = sum(1 for t in txs.values() if t["status"] == "complete")
    total_failed = sum(1 for t in txs.values() if t["status"] == "failed")
    total_pending = sum(1 for t in txs.values() if t["status"] == "pending")

    print(f"\n{'=' * 60}")
    print(f"This run:  +{completed} complete, {failed} failed, {skipped} skipped")
    print(f"Overall:   {total_complete}/{total} complete, {total_failed} failed, {total_pending} pending")

    if server:
        server.shutdown()


if __name__ == "__main__":
    main()
