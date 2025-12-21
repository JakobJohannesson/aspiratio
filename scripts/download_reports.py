"""
Batch download annual reports for all OMXS30 companies.
"""
import sys
import os
import json
from datetime import datetime

# Ensure repo root is in sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from aspiratio.utils.io import read_tsv, write_tsv
from aspiratio.utils.report_downloader import download_company_reports, DownloadError

def main():
    master_path = os.path.join(repo_root, 'instrument_master.csv')
    
    # Read instrument master
    print("Loading instrument master...")
    df = read_tsv(master_path)
    
    # Filter for companies with validated IR URLs
    if 'validated' in df.columns:
        df['validated'] = df['validated'].fillna(False).astype(bool)
        valid_df = df[df['validated'] == True].copy()
    else:
        # If no validation column, use all companies with IR URLs
        valid_df = df[df['investor_relations_url'].notna()].copy()
    
    print(f"Found {len(valid_df)} companies with validated IR URLs\n")
    
    if len(valid_df) == 0:
        print("No companies to process. Run ir_scraper.py first.")
        return
    
    # Download reports for each company
    years = [2019, 2020, 2021, 2022, 2023, 2024]
    all_results = []
    error_count = 0
    
    for idx, row in valid_df.iterrows():
        cid = row['CID']
        company = row['CompanyName']
        ir_url = row['investor_relations_url']
        
        try:
            result = download_company_reports(
                cid=cid,
                company_name=company,
                ir_url=ir_url,
                years=years,
                output_dir=os.path.join(repo_root, 'companies')
            )
            all_results.append(result)
        except DownloadError as e:
            # Site is problematic (repeated failures), skip to next
            print(f"⚠ Download error for {company}: {e}")
            print("  Skipping to next company...")
            error_count += 1
            all_results.append({
                'cid': cid,
                'company': company,
                'found': 0,
                'downloaded': 0,
                'failed': 0,
                'error': str(e),
                'error_type': 'download_error'
            })
        except Exception as e:
            # Other unexpected errors
            print(f"Unexpected error processing {company}: {e}")
            error_count += 1
            all_results.append({
                'cid': cid,
                'company': company,
                'found': 0,
                'downloaded': 0,
                'failed': 0,
                'error': str(e),
                'error_type': 'unknown'
            })
        
        print()  # Blank line between companies
    
    # Save summary report
    summary_path = os.path.join(repo_root, f'download_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    with open(summary_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    
    total_found = sum(r.get('found', 0) for r in all_results)
    total_downloaded = sum(r.get('downloaded', 0) for r in all_results)
    total_skipped = sum(r.get('skipped', 0) for r in all_results)
    total_failed = sum(r.get('failed', 0) for r in all_results)
    
    print(f"Companies processed: {len(all_results)}")
    print(f"Companies with errors: {error_count}")
    print(f"Reports found: {total_found}")
    print(f"Reports downloaded: {total_downloaded}")
    print(f"Reports skipped: {total_skipped}")
    print(f"Reports failed: {total_failed}")
    print(f"\nDetails saved to: {summary_path}")

if __name__ == "__main__":
    main()
