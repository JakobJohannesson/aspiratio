#!/usr/bin/env python3
"""
Redownload failed/incomplete reports one at a time with detailed logging.
For each row where Priority != 'Complete ✓':
  1. Remove existing file if present
  2. Clear file info from coverage table
  3. Attempt download
  4. Validate immediately
  5. Update coverage table
  6. Log result
"""
import pandas as pd
import os
import sys
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aspiratio.utils.report_downloader import find_annual_reports, download_pdf
from aspiratio.utils.playwright_downloader import PLAYWRIGHT_HANDLERS
import asyncio

# Import validation function from validate_reports script
import importlib.util
spec = importlib.util.spec_from_file_location("validate_reports", Path(__file__).parent / "validate_reports.py")
validate_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_module)
validate_pdf = validate_module.validate_pdf

def clear_file_info_for_row(df, idx):
    """Clear file information for a specific row."""
    df.at[idx, 'Report_URL'] = ''
    df.at[idx, 'Source_Page'] = ''
    df.at[idx, 'Size_MB'] = 0.0
    df.at[idx, 'Pages'] = 0
    df.at[idx, 'Validation_Status'] = ''
    df.at[idx, 'Validation_Confidence'] = 0.0
    df.at[idx, 'Validation_Issues'] = ''
    df.at[idx, 'Priority'] = 'Not Downloaded'
    df.at[idx, 'CaptureStatus'] = ''
    return df

def remove_file_if_exists(filepath):
    """Remove file if it exists."""
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
            print(f"  → Removed existing file: {filepath}")
            return True
        except Exception as e:
            print(f"  ✗ Error removing file: {e}")
            return False
    return True

def main():
    """Process incomplete reports one at a time."""
    repo_root = Path(__file__).parent.parent
    coverage_file = repo_root / 'coverage_table_updated.csv'
    instrument_file = repo_root / 'instrument_master.csv'
    
    # Create log file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = repo_root / 'agent_logs' / 'runs' / f'redownload_log_{timestamp}.json'
    log_entries = []
    
    print("="*80)
    print("REDOWNLOAD FAILED/INCOMPLETE REPORTS")
    print("="*80)
    print()
    
    # Load data
    print("Loading data...")
    df = pd.read_csv(coverage_file, sep='\t')
    instruments = pd.read_csv(instrument_file, sep='\t')
    
    # Find rows where Priority != 'Complete ✓'
    incomplete = df[df['Priority'] != 'Complete ✓'].copy()
    total = len(incomplete)
    
    if total == 0:
        print("✓ All reports are complete!")
        return
    
    print(f"Found {total} incomplete reports to reprocess")
    print()
    
    # Group by company for cleaner output
    for company_name in incomplete['CompanyName'].unique():
        company_rows = incomplete[incomplete['CompanyName'] == company_name]
        cid = company_rows.iloc[0]['Company_Identifier']
        
        # Get IR URL from instrument master
        inst_row = instruments[instruments['CID'] == cid]
        if inst_row.empty:
            print(f"✗ {company_name} ({cid}): No IR URL in instrument master")
            continue
        
        ir_url = inst_row.iloc[0]['investor_relations_url']
        
        print("="*80)
        print(f"Company: {company_name} ({cid})")
        print(f"IR URL: {ir_url}")
        print(f"Years to reprocess: {len(company_rows)} - {sorted(company_rows['FiscalYear'].tolist())}")
        print("="*80)
        print()
        
        # Get years needed for this company
        years = sorted(company_rows['FiscalYear'].tolist())
        
        # Find annual reports
        print(f"Searching for annual reports (years: {years})...")
        try:
            reports = find_annual_reports(ir_url, years=years)
            print(f"Found {len(reports)} reports")
            print()
        except Exception as e:
            print(f"✗ Error searching for reports: {e}")
            for _, row in company_rows.iterrows():
                log_entries.append({
                    'company': company_name,
                    'cid': cid,
                    'year': int(row['FiscalYear']),
                    'status': 'search_failed',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
            continue
        
        # Process each year for this company
        for row_num, row in enumerate(company_rows.iterrows(), 1):
            _, row = row
            year = int(row['FiscalYear'])
            idx = row.name
            
            print(f"\n{'='*70}")
            print(f"[Year {year}] Processing report {row_num}/{len(company_rows)}")
            print(f"{'='*70}")
            
            # Step 1: Remove existing file
            existing_file = row.get('Report_URL', '')
            if pd.notna(existing_file) and existing_file:
                # Check if actual file exists in companies folder
                cid = row['Company_Identifier']
                potential_path = repo_root / 'companies' / cid / f"{cid}_{year}_Annual_Report.pdf"
                if potential_path.exists():
                    print(f"→ Removing existing file: {potential_path.name}")
                    remove_file_if_exists(potential_path)
                else:
                    print(f"→ No existing file found at {potential_path}")
            
            # Step 2: Clear file info in dataframe
            print(f"→ Clearing coverage table data for {year}...")
            df = clear_file_info_for_row(df, idx)
            
            # Step 3: Find report for this year
            year_reports = [r for r in reports if r['year'] == year]
            
            if not year_reports:
                print(f"✗ No report URL found for year {year}")
                print(f"  Reason: Search found {len(reports)} reports total, but none matched year {year}")
                
                # Try Playwright fallback if available for this company
                if cid in PLAYWRIGHT_HANDLERS:
                    print(f"→ Attempting Playwright-based download for {company_name}...")
                    try:
                        playwright_result = asyncio.run(PLAYWRIGHT_HANDLERS[cid](year, str(repo_root / 'companies')))
                        
                        if playwright_result['success']:
                            print(f"✓ Playwright download successful!")
                            
                            # Validate
                            output_path = playwright_result['path']
                            validation = validate_pdf(
                                output_path,
                                company_name=company_name,
                                expected_year=year
                            )
                            
                            # Update coverage table
                            df.at[idx, 'Report_URL'] = playwright_result.get('url', 'Playwright download')
                            df.at[idx, 'Source_Page'] = ir_url
                            df.at[idx, 'Size_MB'] = os.path.getsize(output_path) / (1024 * 1024)
                            
                            # Get page count
                            try:
                                import PyPDF2
                                with open(output_path, 'rb') as f:
                                    pdf = PyPDF2.PdfReader(f)
                                    pages = len(pdf.pages)
                                df.at[idx, 'Pages'] = pages
                            except:
                                df.at[idx, 'Pages'] = 0
                            
                            df.at[idx, 'Validation_Status'] = 'Valid' if validation['valid'] else 'Invalid'
                            df.at[idx, 'Validation_Confidence'] = validation.get('confidence', 0.0)
                            df.at[idx, 'Validation_Issues'] = ', '.join(validation.get('issues', []))
                            df.at[idx, 'CaptureStatus'] = 'Playwright'
                            
                            if validation['valid']:
                                df.at[idx, 'Priority'] = 'Complete ✓'
                                print(f"✓ Validation passed: {validation['confidence']:.1f}% confidence")
                            
                            log_entries.append({
                                'company': company_name,
                                'cid': cid,
                                'year': year,
                                'status': 'success_playwright',
                                'url': playwright_result.get('url', ''),
                                'confidence': validation.get('confidence', 0),
                                'timestamp': datetime.now().isoformat()
                            })
                            
                            # Save progress
                            df.to_csv(coverage_file, sep='\t', index=False)
                            continue  # Skip to next year
                            
                    except Exception as e:
                        print(f"✗ Playwright fallback failed: {e}")
                
                log_entries.append({
                    'company': company_name,
                    'cid': cid,
                    'year': year,
                    'status': 'not_found',
                    'error': f'No report URL found for {year} (found {len(reports)} reports for other years)',
                    'timestamp': datetime.now().isoformat()
                })
                # Save progress after each row
                df.to_csv(coverage_file, sep='\t', index=False)
                continue
            
            print(f"→ Found {len(year_reports)} candidate(s) for year {year}")
            for i, rep in enumerate(year_reports, 1):
                print(f"  {i}. {rep.get('title', 'No title')[:60]}")
            print()
            
            # Try each candidate
            downloaded = False
            for candidate_idx, report in enumerate(year_reports):
                url = report['url']
                output_dir = repo_root / 'companies' / cid
                output_path = output_dir / f"{cid}_{year}_Annual_Report.pdf"
                
                if len(year_reports) > 1:
                    print(f"→ Attempting candidate {candidate_idx + 1}/{len(year_reports)}")
                    print(f"  Title: {report.get('title', '')[:70]}")
                    print(f"  URL: {url}")
                
                # Step 4: Download
                result = download_pdf(url, str(output_path), year_hint=year)
                
                if not result['success']:
                    print(f"✗ Download failed: {result['error']}")
                    if candidate_idx < len(year_reports) - 1:
                        print(f"→ Moving to next candidate...")
                        continue
                    else:
                        # Last candidate failed
                        print(f"✗ All candidates exhausted - no valid download for {year}")
                        log_entries.append({
                            'company': company_name,
                            'cid': cid,
                            'year': year,
                            'status': 'download_failed',
                            'url': url,
                            'error': result['error'],
                            'timestamp': datetime.now().isoformat()
                        })
                        break
                
                print(f"✓ Download successful: {result['pages']} pages, {result['size_mb']:.1f} MB")
                print(f"✓ Download successful: {result['pages']} pages, {result['size_mb']:.1f} MB")
                
                # Step 5: Validate immediately
                print(f"→ Validating report...")
                validation = validate_pdf(
                    str(output_path),
                    company_name=company_name,
                    expected_year=year
                )
                
                # Step 6: Update coverage table
                df.at[idx, 'Report_URL'] = url
                df.at[idx, 'Source_Page'] = report.get('source_page', '')
                df.at[idx, 'Size_MB'] = result['size_mb']
                df.at[idx, 'Pages'] = result['pages']
                df.at[idx, 'Validation_Status'] = 'Valid' if validation['valid'] else 'Invalid'
                df.at[idx, 'Validation_Confidence'] = validation.get('confidence', 0.0)
                df.at[idx, 'Validation_Issues'] = ', '.join(validation.get('issues', []))
                df.at[idx, 'CaptureStatus'] = 'Downloaded'
                
                if validation['valid']:
                    df.at[idx, 'Priority'] = 'Complete ✓'
                    print(f"✓ Validation passed: {validation['confidence']:.1f}% confidence")
                    print(f"✓ Report complete for {company_name} {year}")
                    downloaded = True
                    
                    log_entries.append({
                        'company': company_name,
                        'cid': cid,
                        'year': year,
                        'status': 'success',
                        'url': url,
                        'pages': result['pages'],
                        'size_mb': result['size_mb'],
                        'confidence': validation['confidence'],
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    df.at[idx, 'Priority'] = 'Needs Work ⚠'
                    print(f"⚠ Validation found issues:")
                    issues = validation.get('issues', [])
                    for issue in issues:
                        print(f"  - {issue}")
                    
                    # Try next candidate if available
                    if candidate_idx < len(year_reports) - 1:
                        print(f"→ Removing file with validation issues...")
                        remove_file_if_exists(str(output_path))
                        df = clear_file_info_for_row(df, idx)
                        print(f"→ Trying next candidate...")
                        continue
                    
                    log_entries.append({
                        'company': company_name,
                        'cid': cid,
                        'year': year,
                        'status': 'validation_failed',
                        'url': url,
                        'pages': result['pages'],
                        'size_mb': result['size_mb'],
                        'validation_issues': issues,
                        'timestamp': datetime.now().isoformat()
                    })
                
                # Save progress after each row
                df.to_csv(coverage_file, sep='\t', index=False)
                print(f"→ Coverage table updated")
                
                if downloaded:
                    break
            
            print()
    
    # Save final log
    with open(log_file, 'w') as f:
        json.dump(log_entries, f, indent=2)
    
    print("="*80)
    print("SUMMARY")
    print("="*80)
    
    # Count results
    success = sum(1 for e in log_entries if e['status'] == 'success')
    download_failed = sum(1 for e in log_entries if e['status'] == 'download_failed')
    validation_failed = sum(1 for e in log_entries if e['status'] == 'validation_failed')
    not_found = sum(1 for e in log_entries if e['status'] == 'not_found')
    search_failed = sum(1 for e in log_entries if e['status'] == 'search_failed')
    
    print(f"Total processed: {len(log_entries)}")
    print(f"  ✓ Success: {success}")
    print(f"  ⚠ Validation failed: {validation_failed}")
    print(f"  ✗ Download failed: {download_failed}")
    print(f"  ✗ Not found: {not_found}")
    print(f"  ✗ Search failed: {search_failed}")
    print()
    print(f"Log saved to: {log_file}")
    print(f"Coverage table updated: {coverage_file}")

if __name__ == "__main__":
    main()
