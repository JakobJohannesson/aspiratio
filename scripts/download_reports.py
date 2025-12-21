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
    print("="*70)
    print("ANNUAL REPORT BATCH DOWNLOADER")
    print("="*70)
    print()
    
    master_path = os.path.join(repo_root, 'instrument_master.csv')
    coverage_path = os.path.join(repo_root, 'coverage_table_updated.csv')
    
    # Read instrument master
    print("Loading instrument master...")
    df = read_tsv(master_path)
    print(f"✓ Loaded {len(df)} total companies")
    
    # Load coverage table to see what's missing
    print("Loading coverage table to check what's missing...")
    import pandas as pd
    if not os.path.exists(coverage_path):
        print(f"⚠ Coverage table not found at {coverage_path}")
        print("  Run update_coverage_table.py first or all reports will be attempted")
        coverage_df = None
    else:
        coverage_df = pd.read_csv(coverage_path, sep='\t')
        print(f"✓ Loaded coverage table with {len(coverage_df)} entries")
        
        # Get reports that are NOT "Complete ✓" (includes "Not Downloaded" and "Needs Work ⚠")
        missing = coverage_df[coverage_df['Priority'] != 'Complete ✓']
        print(f"✓ Found {len(missing)} reports missing 'Complete ✓' status")
        
        # Break down by priority
        not_downloaded = coverage_df[coverage_df['Priority'] == 'Not Downloaded']
        needs_work = coverage_df[coverage_df['Priority'] == 'Needs Work ⚠']
        print(f"  - {len(not_downloaded)} 'Not Downloaded'")
        print(f"  - {len(needs_work)} 'Needs Work ⚠'")
        
        # Get companies that have missing reports
        companies_with_missing = missing['Company_Identifier'].unique()
        print(f"✓ {len(companies_with_missing)} companies need downloads\n")
    
    # Filter for companies with validated IR URLs
    if 'validated' in df.columns:
        df['validated'] = df['validated'].fillna(False).astype(bool)
        valid_df = df[df['validated'] == True].copy()
    else:
        valid_df = df[df['investor_relations_url'].notna()].copy()
    
    # Further filter to only companies with missing reports
    if coverage_df is not None:
        valid_df = valid_df[valid_df['CID'].isin(companies_with_missing)]
        print(f"Processing {len(valid_df)} companies with missing reports")
    else:
        print(f"Processing all {len(valid_df)} companies")
    
    if len(valid_df) == 0:
        print("\n✓ No missing reports! All companies already downloaded.")
        return
    
    # Download reports for each company
    years = [2019, 2020, 2021, 2022, 2023, 2024]
    print(f"Target years: {', '.join(map(str, years))}")
    print(f"Output directory: companies/\n")
    print("="*70)
    print()
    
    all_results = []
    error_count = 0
    
    for idx, row in valid_df.iterrows():
        cid = row['CID']
        company = row['CompanyName']
        ir_url = row['investor_relations_url']
        
        print(f"[{idx+1}/{len(valid_df)}] Processing: {company} ({cid})")
        print(f"     IR URL: {ir_url}")
        
        try:
            result = download_company_reports(
                cid=cid,
                company_name=company,
                ir_url=ir_url,
                years=years,
                output_dir=os.path.join(repo_root, 'companies')
            )
            all_results.append(result)
            
            # Show summary for this company
            downloaded = result.get('downloaded', 0)
            skipped = result.get('skipped', 0)
            failed = result.get('failed', 0)
            found = result.get('found', 0)
            
            if downloaded > 0:
                print(f"     ✓ Downloaded: {downloaded} report(s)")
            if skipped > 0:
                print(f"     ⊙ Skipped: {skipped} (already exists)")
            if failed > 0:
                print(f"     ✗ Failed: {failed}")
            if found == 0 and downloaded == 0:
                print(f"     ⚠ No reports found")
                
        except DownloadError as e:
            # Site is problematic (repeated failures), skip to next
            print(f"     ⚠ Download error: {e}")
            print(f"     → Skipping to next company...")
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
            print(f"     ✗ Unexpected error: {e}")
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
    
    print(f"{'='*70}")
    print("FINAL SUMMARY")
    print(f"{'='*70}")
    
    total_found = sum(r.get('found', 0) for r in all_results)
    total_downloaded = sum(r.get('downloaded', 0) for r in all_results)
    total_skipped = sum(r.get('skipped', 0) for r in all_results)
    total_failed = sum(r.get('failed', 0) for r in all_results)
    
    print(f"Companies processed:      {len(all_results)}")
    print(f"Companies with errors:    {error_count}")
    print(f"")
    print(f"Reports found:            {total_found}")
    print(f"Reports downloaded:       {total_downloaded}")
    print(f"Reports skipped:          {total_skipped} (already exist)")
    print(f"Reports failed:           {total_failed}")
    print(f"")
    print(f"✓ Details saved to: {summary_path}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
