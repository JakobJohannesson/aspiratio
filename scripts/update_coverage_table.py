"""
Update coverage table with download results and detailed tracking information.
"""
import sys
import os
import json
import pandas as pd
from datetime import datetime
from pathlib import Path

# Ensure repo root is in sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from aspiratio.utils.io import read_tsv, write_tsv

def classify_report_type(title, url, pages):
    """
    Classify the probability that this is an annual report vs other document types.
    Returns (probability_score, document_type, reasoning)
    """
    title_lower = title.lower() if title else ""
    url_lower = url.lower()
    
    # Strong indicators it's an annual report
    annual_indicators = [
        'annual report', 'annual and sustainability', 'årsredovisning',
        'annualreport', 'annual-report', 'arsredovisning'
    ]
    
    # Indicators it might be something else
    quarterly_indicators = ['q1', 'q2', 'q3', 'q4', 'quarter', 'interim', 'quarterly']
    press_indicators = ['press release', 'pr-', 'news']
    form_indicators = ['form sd', 'form 20-f', '10-k', '10-q']
    cmd_indicators = ['capital market', 'cmd', 'investor day']
    
    score = 0.5  # Start neutral
    doc_type = "Unknown"
    reasons = []
    
    # Check for annual report indicators
    for indicator in annual_indicators:
        if indicator in title_lower or indicator in url_lower:
            score += 0.3
            doc_type = "Annual Report"
            reasons.append(f"Contains '{indicator}'")
    
    # Check for other document types
    for indicator in quarterly_indicators:
        if indicator in title_lower or indicator in url_lower:
            score -= 0.4
            doc_type = "Quarterly/Interim Report"
            reasons.append(f"Contains '{indicator}'")
    
    for indicator in press_indicators:
        if indicator in title_lower or indicator in url_lower:
            score -= 0.5
            doc_type = "Press Release"
            reasons.append(f"Contains '{indicator}'")
    
    for indicator in form_indicators:
        if indicator in title_lower or indicator in url_lower:
            score += 0.1  # SEC forms can be annual reports
            doc_type = "SEC Form"
            reasons.append(f"Contains '{indicator}'")
    
    for indicator in cmd_indicators:
        if indicator in title_lower or indicator in url_lower:
            score -= 0.5
            doc_type = "Capital Markets Day"
            reasons.append(f"Contains '{indicator}'")
    
    # Page count heuristic
    if pages:
        if pages >= 80:
            score += 0.2
            reasons.append(f"{pages} pages (typical annual report)")
        elif pages >= 50:
            score += 0.1
            reasons.append(f"{pages} pages (reasonable length)")
        elif pages < 30:
            score -= 0.2
            doc_type = "Short Document"
            reasons.append(f"Only {pages} pages (suspicious)")
    
    # Ensure score is between 0 and 1
    score = max(0.0, min(1.0, score))
    
    reasoning = "; ".join(reasons) if reasons else "No strong indicators"
    
    return score, doc_type, reasoning

def update_coverage_table():
    """Update coverage table with latest download results."""
    
    # Find latest download summary
    summary_files = sorted(Path(repo_root).glob('download_summary_*.json'), reverse=True)
    if not summary_files:
        print("No download summaries found!")
        return
    
    latest_summary = summary_files[0]
    print(f"Using summary: {latest_summary.name}")
    
    with open(latest_summary, 'r') as f:
        results = json.load(f)
    
    # Load instrument master to get company info
    master_path = os.path.join(repo_root, 'instrument_master.csv')
    master_df = read_tsv(master_path)
    
    # Create coverage records
    coverage_records = []
    
    target_years = [2019, 2020, 2021, 2022, 2023, 2024]
    
    for company_result in results:
        cid = company_result['cid']
        company = company_result['company']
        
        # Get IR URL from master
        company_master = master_df[master_df['CID'] == cid]
        ir_url = company_master['investor_relations_url'].values[0] if len(company_master) > 0 else ""
        
        # Check if there was a general error
        general_error = company_result.get('error', None)
        
        # Process each target year
        for year in target_years:
            # Find download info for this year
            download_info = None
            if 'downloads' in company_result:
                for dl in company_result['downloads']:
                    if dl.get('year') == year:
                        download_info = dl
                        break
            
            # Determine status and milestones
            if general_error:
                # Company-level error (couldn't even search)
                status = "Error"
                status_details = general_error
                m1 = "Failed"  # Establish connection
                m2 = "Not Attempted"  # Find object
                m3 = "Not Attempted"  # Download
                m4 = "Not Attempted"  # Validation
                report_url = ""
                source_page = ""
                pages = None
                size_mb = None
                probability = 0.0
                doc_type = "N/A"
                classification_reasoning = general_error
                
            elif download_info:
                dl_status = download_info.get('status')
                
                if dl_status == 'success':
                    status = "Success"
                    status_details = "Successfully downloaded and validated"
                    m1 = "Pass"
                    m2 = "Pass"
                    m3 = "Pass"
                    m4 = "Pass"
                    report_url = download_info.get('url', '')
                    source_page = download_info.get('source_page', ir_url)
                    pages = download_info.get('pages')
                    size_mb = download_info.get('size_mb')
                    
                    # Classify the report
                    title = download_info.get('title', '')
                    probability, doc_type, classification_reasoning = classify_report_type(
                        title, report_url, pages
                    )
                    
                elif dl_status == 'skipped':
                    status = "Skipped"
                    status_details = download_info.get('reason', 'Already exists')
                    m1 = "Pass"
                    m2 = "Pass"
                    m3 = "Skipped"
                    m4 = "Skipped"
                    report_url = "Already downloaded"
                    source_page = ir_url
                    pages = None
                    size_mb = None
                    probability = None
                    doc_type = "Previously Downloaded"
                    classification_reasoning = "Skipped (file already exists)"
                    
                elif dl_status == 'failed':
                    status = "Failed"
                    status_details = download_info.get('error', 'Download failed')
                    m1 = "Pass"
                    m2 = "Pass"
                    m3 = "Failed"
                    m4 = "Not Attempted"
                    report_url = download_info.get('url', '')
                    source_page = download_info.get('source_page', ir_url)
                    pages = None
                    size_mb = None
                    probability = 0.0
                    doc_type = "Failed"
                    classification_reasoning = download_info.get('error', '')
                else:
                    status = "Unknown"
                    status_details = f"Unknown status: {dl_status}"
                    m1 = "Pass"
                    m2 = "Unknown"
                    m3 = "Unknown"
                    m4 = "Unknown"
                    report_url = ""
                    source_page = ir_url
                    pages = None
                    size_mb = None
                    probability = 0.0
                    doc_type = "Unknown"
                    classification_reasoning = ""
            else:
                # No download info for this year (not found)
                status = "Not Found"
                status_details = "Report not found during search"
                m1 = "Pass"
                m2 = "Failed"  # Couldn't find the report
                m3 = "Not Attempted"
                m4 = "Not Attempted"
                report_url = ""
                source_page = ir_url
                pages = None
                size_mb = None
                probability = 0.0
                doc_type = "Not Found"
                classification_reasoning = "No report found for this year"
            
            # Create record
            record = {
                'CompanyName': company,
                'Company_Identifier': cid,
                'What_to_capture': 'Annual report',
                'FiscalYear': year,
                'IR_URL': ir_url,
                'Capture_attempt_date': datetime.now().strftime('%Y-%m-%d'),
                'AgentId': 'A1',
                'CaptureStatus': status,
                'CaptureStatusDetails': status_details,
                'milestone1_Establish_Connection': m1,
                'milestone2_Find_object_to_capture': m2,
                'milestone3_download_object': m3,
                'Milestone4_object_passed_validation': m4,
                'Report_URL': report_url,
                'Source_Page': source_page,
                'Pages': pages if pages else "",
                'Size_MB': f"{size_mb:.2f}" if size_mb else "",
                'Probability_Annual_Report': f"{probability:.2%}" if probability is not None else "",
                'Document_Type': doc_type,
                'Classification_Reasoning': classification_reasoning,
                'User_Agent_Used': 'Rotated (5 variants)',  # We rotate through 5 user agents
            }
            
            coverage_records.append(record)
    
    # Create DataFrame
    coverage_df = pd.DataFrame(coverage_records)
    
    # Save to CSV
    output_path = os.path.join(repo_root, 'coverage_table_updated.csv')
    coverage_df.to_csv(output_path, sep='\t', index=False)
    
    print(f"\n✓ Coverage table updated: {output_path}")
    print(f"  Total records: {len(coverage_records)}")
    print(f"  Companies: {len(results)}")
    print(f"  Years per company: {len(target_years)}")
    
    # Print summary statistics
    print("\nStatus Summary:")
    status_counts = coverage_df['CaptureStatus'].value_counts()
    for status, count in status_counts.items():
        print(f"  {status}: {count}")
    
    print("\nDocument Type Distribution:")
    doc_type_counts = coverage_df[coverage_df['Document_Type'] != '']['Document_Type'].value_counts()
    for doc_type, count in doc_type_counts.head(10).items():
        print(f"  {doc_type}: {count}")
    
    # High confidence annual reports
    prob_df = coverage_df[coverage_df['Probability_Annual_Report'] != ''].copy()
    if len(prob_df) > 0:
        prob_df['prob_numeric'] = prob_df['Probability_Annual_Report'].str.rstrip('%').astype(float)
        high_confidence = prob_df[prob_df['prob_numeric'] >= 80]
        print(f"\nHigh Confidence Annual Reports (≥80%): {len(high_confidence)}")
    else:
        print(f"\nHigh Confidence Annual Reports (≥80%): 0")
    
    return coverage_df

if __name__ == "__main__":
    df = update_coverage_table()
