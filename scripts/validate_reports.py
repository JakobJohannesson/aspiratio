"""
Validate downloaded annual reports and create validated dataset.

This script:
1. Checks all PDFs in companies/ folder
2. Validates: page count, company name, year mentions
3. Copies validated PDFs to companies_validated/
4. Creates validation_results.csv for feedback
5. Identifies successful patterns for future downloads
"""

import os
import re
import csv
import shutil
from pathlib import Path
from datetime import datetime
from PyPDF2 import PdfReader
import pandas as pd

# Minimum pages for a valid annual report
MIN_PAGES = 50
MAX_PAGES = 500

# Company name variations to check for
def get_company_variations(company_name):
    """Generate variations of company name to search in PDF."""
    variations = [company_name]
    
    # Remove common suffixes
    base_name = re.sub(r'\s+(AB|Ltd|Group|Inc|Corp|Plc|A|B)$', '', company_name, flags=re.IGNORECASE)
    if base_name != company_name:
        variations.append(base_name)
    
    # Add uppercase version
    variations.append(company_name.upper())
    
    return list(set(variations))

def extract_text_sample(pdf_path, max_pages=5):
    """Extract text from first few pages of PDF."""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        
        for i in range(min(max_pages, len(reader.pages))):
            page = reader.pages[i]
            text += page.extract_text() + "\n"
        
        return text
    except Exception as e:
        return f"ERROR: {str(e)}"

def validate_pdf(pdf_path, company_name, expected_year):
    """
    Validate a PDF annual report.
    
    Returns:
        dict: {
            'valid': bool,
            'pages': int,
            'company_found': bool,
            'year_found': bool,
            'issues': list of str,
            'confidence': float (0-100)
        }
    """
    result = {
        'valid': False,
        'pages': 0,
        'company_found': False,
        'year_found': False,
        'issues': [],
        'confidence': 0.0
    }
    
    try:
        # Check file exists and is readable
        if not os.path.exists(pdf_path):
            result['issues'].append('File not found')
            return result
        
        # Get page count
        reader = PdfReader(pdf_path)
        page_count = len(reader.pages)
        result['pages'] = page_count
        
        # Check page count
        if page_count < MIN_PAGES:
            result['issues'].append(f'Too few pages ({page_count} < {MIN_PAGES})')
        elif page_count > MAX_PAGES:
            result['issues'].append(f'Suspiciously many pages ({page_count} > {MAX_PAGES})')
        
        # Extract text from first few pages
        text_sample = extract_text_sample(pdf_path, max_pages=5)
        
        if text_sample.startswith('ERROR'):
            result['issues'].append(f'Cannot extract text: {text_sample}')
            return result
        
        # Normalize text for searching
        text_normalized = text_sample.lower()
        
        # Check for company name
        company_variations = get_company_variations(company_name)
        for variation in company_variations:
            if variation.lower() in text_normalized:
                result['company_found'] = True
                break
        
        if not result['company_found']:
            result['issues'].append(f'Company name "{company_name}" not found in PDF')
        
        # Check for year mentions
        year_patterns = [
            str(expected_year),  # 2024
            f'{expected_year-1}/{expected_year % 100}',  # 2023/24
            f'{expected_year-1}-{expected_year % 100}',  # 2023-24
            f'annual report {expected_year}',
            f'årsredovisning {expected_year}',
        ]
        
        year_found = False
        for pattern in year_patterns:
            if pattern.lower() in text_normalized:
                year_found = True
                break
        
        result['year_found'] = year_found
        
        if not year_found:
            result['issues'].append(f'Year {expected_year} not found in PDF')
        
        # Calculate confidence score
        confidence = 0
        
        # Page count (0-40 points)
        if MIN_PAGES <= page_count <= MAX_PAGES:
            page_score = min(40, (page_count - MIN_PAGES) / (200 - MIN_PAGES) * 40)
            confidence += page_score
        
        # Company name found (30 points)
        if result['company_found']:
            confidence += 30
        
        # Year found (30 points)
        if result['year_found']:
            confidence += 30
        
        result['confidence'] = round(confidence, 1)
        
        # Determine if valid (high confidence threshold)
        result['valid'] = (
            result['confidence'] >= 60 and
            result['company_found'] and
            result['year_found'] and
            MIN_PAGES <= page_count <= MAX_PAGES
        )
        
        return result
        
    except Exception as e:
        result['issues'].append(f'Validation error: {str(e)}')
        return result

def load_instrument_master():
    """Load company information from instrument_master.csv."""
    df = pd.read_csv('instrument_master.csv', sep='\t')
    
    companies = {}
    for _, row in df.iterrows():
        cid = row['CID']
        companies[cid] = {
            'name': row['CompanyName'],
            'isin': row.get('ISIN', ''),
            'ir_url': row.get('investor_relations_url', '')
        }
    
    return companies

def scan_downloaded_reports(companies_dir='companies'):
    """Scan companies directory for downloaded PDFs."""
    reports = []
    
    companies_path = Path(companies_dir)
    if not companies_path.exists():
        print(f"Error: {companies_dir} directory not found")
        return reports
    
    for company_dir in companies_path.iterdir():
        if not company_dir.is_dir():
            continue
        
        cid = company_dir.name
        
        for pdf_file in company_dir.glob('*.pdf'):
            # Extract year from filename (annual_report_2024.pdf)
            year_match = re.search(r'(\d{4})', pdf_file.name)
            if year_match:
                year = int(year_match.group(1))
                reports.append({
                    'cid': cid,
                    'year': year,
                    'path': str(pdf_file),
                    'filename': pdf_file.name
                })
    
    return reports

def main():
    print("="*70)
    print("PDF VALIDATION SCRIPT")
    print("="*70)
    print()
    
    # Load company information
    print("Loading company information...")
    companies = load_instrument_master()
    print(f"✓ Loaded {len(companies)} companies\n")
    
    # Load already validated reports from coverage table
    already_validated = set()
    coverage_file = 'coverage_table_updated.csv'
    if os.path.exists(coverage_file):
        try:
            coverage_df = pd.read_csv(coverage_file, sep='\t')
            # Get reports that are already validated and complete
            validated = coverage_df[
                (coverage_df['Validation_Status'] == 'Valid') & 
                (coverage_df['Priority'] == 'Complete ✓')
            ]
            for _, row in validated.iterrows():
                cid = row['Company_Identifier']
                year = row['FiscalYear']
                already_validated.add((cid, year))
            
            if already_validated:
                print(f"Found {len(already_validated)} already validated reports (will skip)")
        except Exception as e:
            print(f"Note: Could not load previous validation status: {e}")
    
    # Scan for downloaded reports
    print("Scanning for downloaded PDFs...")
    all_reports = scan_downloaded_reports()
    
    # Filter out already validated reports
    reports = [r for r in all_reports if (r['cid'], r['year']) not in already_validated]
    
    print(f"✓ Found {len(all_reports)} PDF files")
    if already_validated:
        print(f"  - {len(all_reports) - len(reports)} already validated (skipped)")
        print(f"  - {len(reports)} to validate\n")
    else:
        print()
    
    if not reports:
        print("No new PDFs to validate. All reports are already validated!")
        return
    
    # Create output directories
    validated_dir = Path('companies_validated')
    validated_dir.mkdir(exist_ok=True)
    
    # Validate each report
    print("Validating reports...")
    print("-"*70)
    
    validation_results = []
    valid_count = 0
    
    for i, report in enumerate(reports, 1):
        cid = report['cid']
        year = report['year']
        pdf_path = report['path']
        
        company_info = companies.get(cid, {})
        company_name = company_info.get('name', cid)
        
        print(f"\n[{i}/{len(reports)}] {company_name} - {year}")
        print(f"  File: {report['filename']}")
        
        # Validate
        validation = validate_pdf(pdf_path, company_name, year)
        
        # Print results
        status = "✓ VALID" if validation['valid'] else "✗ INVALID"
        print(f"  {status} - Confidence: {validation['confidence']}%")
        print(f"  Pages: {validation['pages']}, Company: {'✓' if validation['company_found'] else '✗'}, Year: {'✓' if validation['year_found'] else '✗'}")
        
        if validation['issues']:
            for issue in validation['issues']:
                print(f"    ⚠ {issue}")
        
        # Copy to validated folder if valid
        if validation['valid']:
            valid_count += 1
            dest_dir = validated_dir / cid
            dest_dir.mkdir(exist_ok=True)
            dest_path = dest_dir / report['filename']
            shutil.copy2(pdf_path, dest_path)
            print(f"  → Copied to {dest_path}")
        
        # Store results
        validation_results.append({
            'CID': cid,
            'Company_Name': company_name,
            'Year': year,
            'Filename': report['filename'],
            'Valid': validation['valid'],
            'Confidence': validation['confidence'],
            'Pages': validation['pages'],
            'Company_Found': validation['company_found'],
            'Year_Found': validation['year_found'],
            'Issues': '; '.join(validation['issues']) if validation['issues'] else '',
            'Source_Path': pdf_path,
            'Validated_Date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'IR_URL': company_info.get('ir_url', ''),
            'Pattern_Type': 'To be analyzed'
        })
    
    # Save results to CSV
    print("\n" + "="*70)
    print("SAVING RESULTS")
    print("="*70)
    
    results_df = pd.DataFrame(validation_results)
    results_file = 'validation_results.csv'
    results_df.to_csv(results_file, index=False)
    print(f"✓ Saved validation results to {results_file}")
    
    # Summary statistics
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total PDFs scanned:     {len(reports)}")
    print(f"Valid reports:          {valid_count} ({valid_count/len(reports)*100:.1f}%)")
    print(f"Invalid reports:        {len(reports) - valid_count}")
    print(f"\nValidated PDFs copied to: {validated_dir}/")
    print(f"Validation results saved to: {results_file}")
    
    # Show validation by company
    print("\n" + "="*70)
    print("VALIDATION BY COMPANY")
    print("="*70)
    
    company_stats = results_df.groupby('Company_Name').agg({
        'Valid': ['sum', 'count'],
        'Confidence': 'mean'
    }).round(1)
    
    company_stats.columns = ['Valid', 'Total', 'Avg_Confidence']
    company_stats = company_stats.sort_values('Valid', ascending=False)
    
    for company, row in company_stats.iterrows():
        status = "✓" if row['Valid'] == row['Total'] else "⚠"
        print(f"{status} {company:30s} {int(row['Valid'])}/{int(row['Total'])} valid (avg confidence: {row['Avg_Confidence']:.1f}%)")
    
    # Identify successful patterns
    print("\n" + "="*70)
    print("SUCCESSFUL PATTERNS (for future downloads)")
    print("="*70)
    
    successful = results_df[results_df['Valid'] == True]
    if len(successful) > 0:
        # Group by company to identify consistent success
        success_by_company = successful.groupby('CID').agg({
            'Year': 'count',
            'Confidence': 'mean',
            'IR_URL': 'first',
            'Company_Name': 'first'
        }).round(1)
        
        success_by_company = success_by_company[success_by_company['Year'] >= 3]  # At least 3 valid reports
        success_by_company = success_by_company.sort_values('Year', ascending=False)
        
        if len(success_by_company) > 0:
            print("\nCompanies with 3+ validated reports (use as examples):")
            for cid, row in success_by_company.iterrows():
                print(f"  ✓ {row['Company_Name']:30s} - {int(row['Year'])} reports, {row['Confidence']:.1f}% avg confidence")
                print(f"    IR URL: {row['IR_URL']}")
        else:
            print("  No companies with 3+ validated reports yet")
    else:
        print("  No valid reports found")
    
    # Update coverage_table_updated.csv with validation results
    print("\n" + "="*70)
    print("UPDATING COVERAGE TABLE WITH VALIDATION RESULTS")
    print("="*70)
    
    try:
        coverage_file = 'coverage_table_updated.csv'
        if os.path.exists(coverage_file):
            coverage_df = pd.read_csv(coverage_file, sep='\t')
            
            print(f"Loaded coverage table with {len(coverage_df)} rows")
            
            # Add validation columns if they don't exist
            if 'Validation_Status' not in coverage_df.columns:
                coverage_df['Validation_Status'] = ''
            if 'Validation_Confidence' not in coverage_df.columns:
                coverage_df['Validation_Confidence'] = ''
            if 'Validation_Issues' not in coverage_df.columns:
                coverage_df['Validation_Issues'] = ''
            if 'Validation_Date' not in coverage_df.columns:
                coverage_df['Validation_Date'] = ''
            if 'Priority' not in coverage_df.columns:
                coverage_df['Priority'] = ''
            if 'Failure_Reason' not in coverage_df.columns:
                coverage_df['Failure_Reason'] = ''
            
            # Update each row with validation results
            updated_count = 0
            passed_count = 0
            failed_count = 0
            
            for idx, row in coverage_df.iterrows():
                cid = row['Company_Identifier']
                year = row['FiscalYear']
                
                # Find matching validation result
                match = results_df[(results_df['CID'] == cid) & (results_df['Year'] == year)]
                
                if len(match) > 0:
                    validation = match.iloc[0]
                    
                    # Update validation tracking columns
                    coverage_df.at[idx, 'Validation_Status'] = 'Valid' if validation['Valid'] else 'Invalid'
                    coverage_df.at[idx, 'Validation_Confidence'] = f"{validation['Confidence']}%"
                    coverage_df.at[idx, 'Validation_Issues'] = validation['Issues'] if validation['Issues'] else ''
                    coverage_df.at[idx, 'Validation_Date'] = validation['Validated_Date']
                    
                    # Update Milestone 4 (validation)
                    if validation['Valid']:
                        coverage_df.at[idx, 'Milestone4_object_passed_validation'] = 'Pass'
                        # Update overall status to Downloaded (validated)
                        if row['CaptureStatus'] != 'Downloaded':
                            coverage_df.at[idx, 'CaptureStatus'] = 'Downloaded'
                            coverage_df.at[idx, 'CaptureStatusDetails'] = f"Successfully validated: {validation['Pages']} pages, {validation['Confidence']}% confidence"
                        # Mark as complete - no further action needed
                        coverage_df.at[idx, 'Priority'] = 'Complete ✓'
                        coverage_df.at[idx, 'Failure_Reason'] = ''  # Clear any previous failure reason
                        passed_count += 1
                    else:
                        coverage_df.at[idx, 'Milestone4_object_passed_validation'] = 'Failed'
                        # Update status to reflect validation failure
                        coverage_df.at[idx, 'CaptureStatus'] = 'Validation Failed'
                        coverage_df.at[idx, 'CaptureStatusDetails'] = f"Validation failed: {validation['Issues']}"
                        # Mark as needing attention
                        coverage_df.at[idx, 'Priority'] = 'Needs Work ⚠'
                        coverage_df.at[idx, 'Failure_Reason'] = f"Validation failed: {validation['Issues']}"
                        failed_count += 1
                    
                    updated_count += 1
                else:
                    # No validation data - PDF not yet downloaded
                    if row.get('CaptureStatus') not in ['Downloaded', 'Validation Failed']:
                        coverage_df.at[idx, 'Priority'] = 'Not Downloaded'
            
            # Save updated coverage table
            coverage_df.to_csv(coverage_file, sep='\t', index=False)
            print(f"✓ Updated {updated_count} rows in coverage table")
            print(f"  - {passed_count} passed validation (Milestone 4: Pass, Priority: Complete ✓)")
            print(f"  - {failed_count} failed validation (Milestone 4: Failed, Priority: Needs Work ⚠)")
            print(f"✓ Saved to {coverage_file}")
            
            # Show priority summary
            print("\n" + "-"*70)
            print("PRIORITY SUMMARY (focus on what needs work)")
            print("-"*70)
            
            priority_counts = coverage_df['Priority'].value_counts()
            total_rows = len(coverage_df)
            
            if 'Complete ✓' in priority_counts:
                pct = (priority_counts['Complete ✓'] / total_rows * 100)
                print(f"✓ Complete (validated):      {priority_counts['Complete ✓']:3d} / {total_rows} ({pct:.1f}%)")
            
            if 'Needs Work ⚠' in priority_counts:
                pct = (priority_counts['Needs Work ⚠'] / total_rows * 100)
                print(f"⚠ Needs Work (failed):       {priority_counts['Needs Work ⚠']:3d} / {total_rows} ({pct:.1f}%)")
            
            if 'Not Downloaded' in priority_counts:
                pct = (priority_counts['Not Downloaded'] / total_rows * 100)
                print(f"○ Not Downloaded:            {priority_counts['Not Downloaded']:3d} / {total_rows} ({pct:.1f}%)")
            
            print("\n✓ Focus development efforts on 'Needs Work' and 'Not Downloaded' entries")
            print("✓ Companies marked 'Complete' have fully validated reports")
            
        else:
            print(f"⚠ Coverage table not found: {coverage_file}")
            print("  Run update_coverage_table.py first to create it")
    
    except Exception as e:
        print(f"✗ Error updating coverage table: {e}")

if __name__ == '__main__':
    main()
