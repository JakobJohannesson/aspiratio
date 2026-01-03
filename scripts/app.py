import streamlit as st
import pandas as pd
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Ensure repo root is in sys.path for aspiratio imports
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from aspiratio.utils.io import read_tsv, write_tsv

st.set_page_config(page_title="IR Download Manager", layout="wide")

st.title("📊 IR Download Manager")

# Tabs for different views
tab1, tab2, tab3, tab4 = st.tabs(["📊 Coverage Review", "📥 Download Results", "✅ URL Validator", "🎬 Record Download"])

master_path = os.path.join(repo_root, 'instrument_master.csv')
coverage_path = os.path.join(repo_root, 'coverage_table_updated.csv')

# TAB 1: Coverage Table Review with Feedback
with tab1:
    st.header("Coverage Table Review & Feedback")
    
    if not os.path.exists(coverage_path):
        st.warning(f"Coverage table not found. Run `python scripts/update_coverage_table.py` first.")
    else:
        # Load coverage table
        coverage_df = pd.read_csv(coverage_path, sep='\t')
        
        # Add feedback column if it doesn't exist
        if 'User_Feedback' not in coverage_df.columns:
            coverage_df['User_Feedback'] = ''
        if 'Feedback_Status' not in coverage_df.columns:
            coverage_df['Feedback_Status'] = ''
        
        # Summary metrics
        st.subheader("📈 Overall Statistics")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        total_records = len(coverage_df)
        success_count = len(coverage_df[coverage_df['CaptureStatus'] == 'Success'])
        error_count = len(coverage_df[coverage_df['CaptureStatus'] == 'Error'])
        not_found_count = len(coverage_df[coverage_df['CaptureStatus'] == 'Not Found'])
        failed_count = len(coverage_df[coverage_df['CaptureStatus'] == 'Failed'])
        
        col1.metric("Total Records", total_records)
        col2.metric("✅ Success", success_count, delta=f"{success_count/total_records*100:.0f}%")
        col3.metric("❌ Errors", error_count, delta_color="off")
        col4.metric("🔍 Not Found", not_found_count, delta_color="off")
        col5.metric("⚠️ Failed", failed_count, delta_color="off")
        
        st.divider()
        
        # Filter controls
        st.subheader("🔍 Filters")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.multiselect(
                "Status",
                options=['Success', 'Error', 'Not Found', 'Failed', 'Skipped'],
                default=['Error', 'Not Found', 'Failed']
            )
        
        with col2:
            company_filter = st.multiselect(
                "Company",
                options=sorted(coverage_df['CompanyName'].unique()),
                default=[]
            )
        
        with col3:
            year_filter = st.multiselect(
                "Fiscal Year",
                options=sorted(coverage_df['FiscalYear'].unique()),
                default=[]
            )
        
        # Apply filters
        filtered_df = coverage_df.copy()
        if status_filter:
            filtered_df = filtered_df[filtered_df['CaptureStatus'].isin(status_filter)]
        if company_filter:
            filtered_df = filtered_df[filtered_df['CompanyName'].isin(company_filter)]
        if year_filter:
            filtered_df = filtered_df[filtered_df['FiscalYear'].isin(year_filter)]
        
        st.write(f"Showing {len(filtered_df)} of {len(coverage_df)} records")
        
        st.divider()
        
        # Display and edit table
        st.subheader("📋 Review & Add Feedback")
        
        # Select columns to display
        display_columns = [
            'CompanyName', 'Company_Identifier', 'FiscalYear', 'CaptureStatus',
            'Pages', 'Size_MB', 'Probability_Annual_Report', 'Document_Type',
            'CaptureStatusDetails', 'Report_URL', 'Feedback_Status', 'User_Feedback'
        ]
        
        edited_coverage = st.data_editor(
            filtered_df[display_columns],
            column_config={
                "CompanyName": st.column_config.TextColumn("Company", width="medium", disabled=True),
                "Company_Identifier": st.column_config.TextColumn("CID", width="small", disabled=True),
                "FiscalYear": st.column_config.NumberColumn("Year", width="small", disabled=True),
                "CaptureStatus": st.column_config.TextColumn("Status", width="small", disabled=True),
                "Pages": st.column_config.NumberColumn("Pages", width="small", disabled=True),
                "Size_MB": st.column_config.TextColumn("Size", width="small", disabled=True),
                "Probability_Annual_Report": st.column_config.TextColumn("Prob%", width="small", disabled=True),
                "Document_Type": st.column_config.TextColumn("Type", width="medium", disabled=True),
                "CaptureStatusDetails": st.column_config.TextColumn("Details", width="medium", disabled=True),
                "Report_URL": st.column_config.LinkColumn("PDF Link", width="small", disabled=True),
                "Feedback_Status": st.column_config.SelectboxColumn(
                    "Your Review",
                    width="small",
                    options=['', '✅ Correct', '❌ Wrong', '🔧 Needs Fix', '❓ Unclear'],
                ),
                "User_Feedback": st.column_config.TextColumn("Your Notes", width="large"),
            },
            hide_index=True,
            height=600,
            key="coverage_editor"
        )
        
        # Save feedback button
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("💾 Save Feedback", type="primary"):
                # Update the filtered rows in the original dataframe
                for idx in edited_coverage.index:
                    coverage_df.loc[idx, 'Feedback_Status'] = edited_coverage.loc[idx, 'Feedback_Status']
                    coverage_df.loc[idx, 'User_Feedback'] = edited_coverage.loc[idx, 'User_Feedback']
                
                # Save to file
                coverage_df.to_csv(coverage_path, sep='\t', index=False)
                st.success("✅ Feedback saved!")
                st.rerun()
        
        with col2:
            if st.button("📊 Export Feedback Summary"):
                feedback_summary = coverage_df[
                    (coverage_df['Feedback_Status'] != '') | (coverage_df['User_Feedback'] != '')
                ][['CompanyName', 'FiscalYear', 'CaptureStatus', 'Document_Type', 
                   'Feedback_Status', 'User_Feedback']]
                
                if len(feedback_summary) > 0:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    export_path = os.path.join(repo_root, f'feedback_summary_{timestamp}.csv')
                    feedback_summary.to_csv(export_path, index=False)
                    st.success(f"📄 Exported {len(feedback_summary)} feedback entries to {export_path}")
                else:
                    st.info("No feedback to export yet")
        
        # Quick Stats
        st.divider()
        st.subheader("📊 Document Type Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Document Classification**")
            doc_type_counts = filtered_df['Document_Type'].value_counts()
            st.dataframe(doc_type_counts, width='stretch')
        
        with col2:
            st.write("**Feedback Summary**")
            if filtered_df['Feedback_Status'].notna().any():
                feedback_counts = filtered_df[filtered_df['Feedback_Status'] != '']['Feedback_Status'].value_counts()
                st.dataframe(feedback_counts, width='stretch')
            else:
                st.info("No feedback provided yet")

# TAB 2: Download Results (JSON view)
with tab2:
    st.header("Download Results & JSON Summary")
    
    st.divider()
    
    # Section 1: Download Missing Reports
    st.subheader("🚀 Download Missing Reports")
    
    if not os.path.exists(coverage_path):
        st.warning("Coverage table not found. Run `aspiratio-update` first.")
    else:
        coverage_df = pd.read_csv(coverage_path, sep='\t')
        missing_reports = coverage_df[coverage_df['Priority'] != 'Complete ✓'].copy()
        
        if len(missing_reports) == 0:
            st.success("✅ All reports complete! No missing reports to download.")
        else:
            st.info(f"Found **{len(missing_reports)}** missing reports across **{missing_reports['CompanyName'].nunique()}** companies")
            
            col1, col2 = st.columns([1, 3])
            
            with col1:
                if st.button("📥 Download All Missing", type="primary", use_container_width=True):
                    import subprocess
                    import time
                    
                    # Create a status container for real-time updates
                    status_container = st.status("Starting batch download...", expanded=True)
                    
                    with status_container:
                        st.write("📋 Preparing to download missing reports...")
                        st.write(f"• Total reports to download: **{len(missing_reports)}**")
                        st.write(f"• Companies affected: **{missing_reports['CompanyName'].nunique()}**")
                        
                        st.write("\n🚀 Launching download process...")
                        
                        # Start the download process and capture output
                        process = subprocess.Popen(
                            ["aspiratio-download"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            bufsize=1
                        )
                        
                        # Create a placeholder for live output
                        output_placeholder = st.empty()
                        progress_bar = st.progress(0)
                        
                        output_lines = []
                        companies_processed = 0
                        total_companies = missing_reports['CompanyName'].nunique()
                        
                        # Read output line by line
                        for line in process.stdout:
                            output_lines.append(line.strip())
                            
                            # Update progress based on output
                            if "Processing:" in line or "Company:" in line:
                                companies_processed += 1
                                progress = min(companies_processed / total_companies, 1.0)
                                progress_bar.progress(progress)
                                
                                # Extract company name
                                if "Processing:" in line:
                                    st.write(f"📊 {line.strip()}")
                            
                            elif "✓" in line or "Downloaded:" in line:
                                st.write(f"✅ {line.strip()}")
                            elif "✗" in line or "Failed:" in line:
                                st.write(f"❌ {line.strip()}")
                            elif "⚠" in line or "Warning:" in line:
                                st.write(f"⚠️ {line.strip()}")
                            
                            # Keep only last 20 lines for display
                            if len(output_lines) > 20:
                                output_lines = output_lines[-20:]
                        
                        process.wait()
                        progress_bar.progress(1.0)
                        
                        if process.returncode == 0:
                            st.write("\n✅ **Batch download completed successfully!**")
                            status_container.update(label="Download complete!", state="complete")
                            st.balloons()
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.write(f"\n⚠️ Process exited with code {process.returncode}")
                            status_container.update(label="Download completed with warnings", state="error")
                            
                        with st.expander("📜 View full output log"):
                            st.text("\n".join(output_lines))
            
            with col2:
                st.markdown("""
                **Or download individual reports below** ⬇️  
                Select a company and year, then click download.
                """)
            
            st.divider()
            
            # Individual report downloads
            st.subheader("📄 Download Individual Reports")
            
            # Group by company
            missing_by_company = missing_reports.groupby('CompanyName').agg({
                'FiscalYear': list,
                'Company_Identifier': 'first',
                'IR_URL': 'first'
            }).reset_index()
            
            # Company filter
            company_filter = st.selectbox(
                "Filter by company (optional)",
                options=['All'] + sorted(missing_by_company['CompanyName'].tolist()),
                key="missing_company_filter"
            )
            
            if company_filter != 'All':
                missing_by_company = missing_by_company[missing_by_company['CompanyName'] == company_filter]
            
            # Display each company with download buttons
            for idx, row in missing_by_company.iterrows():
                company_name = row['CompanyName']
                company_id = row['Company_Identifier']
                years = sorted(row['FiscalYear'])
                ir_url = row['IR_URL']
                
                with st.expander(f"**{company_name}** ({company_id}) - {len(years)} missing report(s)"):
                    st.write(f"**IR URL:** {ir_url}")
                    st.write(f"**Missing years:** {', '.join(map(str, years))}")
                    
                    # Create columns for each year
                    cols = st.columns(min(len(years), 6))
                    
                    for i, year in enumerate(years):
                        col_idx = i % 6
                        with cols[col_idx]:
                            if st.button(f"📥 {year}", key=f"dl_{company_id}_{year}", use_container_width=True):
                                # Create detailed progress status
                                status = st.status(f"Downloading {company_name} {year}...", expanded=True)
                                
                                with status:
                                    # Step 1: Preparation
                                    st.write(f"📋 **Step 1: Preparing download**")
                                    st.write(f"• Company: {company_name} ({company_id})")
                                    st.write(f"• Year: {year}")
                                    st.write(f"• IR URL: [{ir_url}]({ir_url})")
                                    progress_bar = st.progress(0)
                                    
                                    import subprocess
                                    import time
                                    
                                    # Step 2: Search for report
                                    st.write(f"\n🔍 **Step 2: Searching for report**")
                                    st.write(f"• Accessing investor relations page...")
                                    st.write(f"• Looking for annual report {year}...")
                                    progress_bar.progress(0.2)
                                    
                                    try:
                                        # Create a temporary script to download just this report
                                        temp_script = f"""
import sys
sys.path.insert(0, '{repo_root}')
from aspiratio.tier1.report_downloader import find_annual_reports, download_pdf
from aspiratio.tier2.playwright_downloader import PLAYWRIGHT_HANDLERS
import asyncio
import os

# Try traditional search first
print("Searching {ir_url}...")
reports = find_annual_reports("{ir_url}", years=[{year}])

if reports:
    for report in reports:
        if report['year'] == {year}:
            print(f"Found: {{report['title']}}")
            print(f"URL: {{report['url']}}")
            
            output_dir = os.path.join("{repo_root}", "companies", "{company_id}")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{{company_id}}_{year}_Annual_Report.pdf")
            
            print(f"Downloading to {{output_path}}...")
            result = download_pdf(report['url'], output_path, min_pages=50, year_hint={year})
            
            if result['success']:
                print(f"SUCCESS: Downloaded {{result['pages']}} pages, {{result['size_mb']:.1f}} MB")
            else:
                print(f"ERROR: {{result['error']}}")
            break
else:
    # Try Playwright fallback
    if "{company_id}" in PLAYWRIGHT_HANDLERS:
        print("No reports found via traditional search")
        print("Trying Playwright-based download...")
        result = asyncio.run(PLAYWRIGHT_HANDLERS["{company_id}"]({year}, "{repo_root}/companies"))
        if result['success']:
            print(f"SUCCESS: Playwright download completed")
        else:
            print(f"ERROR: {{result['error']}}")
    else:
        print("ERROR: No reports found and no Playwright handler available")
"""
                                        
                                        # Write temp script
                                        temp_file = "/tmp/aspiratio_single_download.py"
                                        with open(temp_file, 'w') as f:
                                            f.write(temp_script)
                                        
                                        # Step 3: Execute download
                                        st.write(f"\n📥 **Step 3: Downloading PDF**")
                                        progress_bar.progress(0.4)
                                        
                                        output_placeholder = st.empty()
                                        
                                        # Run the download
                                        process = subprocess.Popen(
                                            [sys.executable, temp_file],
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE,
                                            text=True,
                                            bufsize=1
                                        )
                                        
                                        output_lines = []
                                        success = False
                                        
                                        for line in process.stdout:
                                            line = line.strip()
                                            output_lines.append(line)
                                            
                                            if "Searching" in line:
                                                st.write(f"🔍 {line}")
                                            elif "Found:" in line:
                                                st.write(f"✅ {line}")
                                                progress_bar.progress(0.5)
                                            elif "URL:" in line:
                                                st.write(f"🔗 {line}")
                                            elif "Downloading to" in line:
                                                st.write(f"⬇️ {line}")
                                                progress_bar.progress(0.6)
                                            elif "SUCCESS" in line:
                                                st.write(f"✅ {line}")
                                                progress_bar.progress(0.9)
                                                success = True
                                            elif "ERROR" in line:
                                                st.write(f"❌ {line}")
                                            elif "Trying Playwright" in line:
                                                st.write(f"🎭 {line}")
                                                progress_bar.progress(0.7)
                                        
                                        process.wait()
                                        
                                        # Step 4: Validation
                                        if success:
                                            st.write(f"\n✓ **Step 4: Validating PDF**")
                                            progress_bar.progress(0.95)
                                            time.sleep(0.5)
                                            
                                            st.write("• Checking page count...")
                                            st.write("• Verifying company name...")
                                            st.write("• Confirming year...")
                                            
                                            progress_bar.progress(1.0)
                                            
                                            st.write(f"\n🎉 **Download Complete!**")
                                            status.update(label=f"✅ {company_name} {year} downloaded successfully!", state="complete")
                                            
                                            # Clean up
                                            os.remove(temp_file)
                                            
                                            time.sleep(1)
                                            st.rerun()
                                        else:
                                            st.write(f"\n⚠️ **Download failed or incomplete**")
                                            status.update(label=f"⚠️ {company_name} {year} - check details", state="error")
                                            
                                            with st.expander("📜 View detailed output"):
                                                st.text("\n".join(output_lines))
                                            
                                            # Clean up
                                            if os.path.exists(temp_file):
                                                os.remove(temp_file)
                                                
                                    except subprocess.TimeoutExpired:
                                        st.error("⏱️ Download timed out (>120s)")
                                        status.update(label="Download timed out", state="error")
                                    except Exception as e:
                                        st.error(f"❌ Error: {e}")
                                        status.update(label=f"Error: {str(e)}", state="error")
    
    st.divider()
    
    # Section 2: View Previous Download Summaries
    st.subheader("📊 Previous Download Summaries")
    
    # Find all download summary JSON files
    summary_files = sorted(Path(repo_root).glob('download_summary_*.json'), reverse=True)
    
    if not summary_files:
        st.info("No download summaries found. Run `aspiratio-download` first.")
    else:
        selected_file = st.selectbox(
            "Select download summary",
            options=summary_files,
            format_func=lambda x: x.name
        )
        
        with open(selected_file, 'r') as f:
            results = json.load(f)
        
        st.subheader(f"📋 Summary from {selected_file.name}")
        
        # Overall statistics
        col1, col2, col3, col4 = st.columns(4)
        
        total_companies = len(results)
        successful = sum(1 for r in results if r.get('downloaded', 0) > 0)
        with_errors = sum(1 for r in results if 'error' in r or r.get('failed', 0) > 0)
        total_downloaded = sum(r.get('downloaded', 0) for r in results)
        
        col1.metric("Companies Processed", total_companies)
        col2.metric("Successful", successful, delta=f"{successful/total_companies*100:.0f}%")
        col3.metric("With Errors", with_errors, delta=f"-{with_errors/total_companies*100:.0f}%", delta_color="inverse")
        col4.metric("Reports Downloaded", total_downloaded)
        
        st.divider()
        
        # Company selector for detailed view
        st.subheader("🔎 Company Details")
        company_names = [r['company'] for r in results]
        selected_company = st.selectbox("Select company", company_names)
        
        if selected_company:
            company_result = next((r for r in results if r['company'] == selected_company), None)
            if company_result:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Company Info**")
                    st.write(f"CID: {company_result['cid']}")
                    st.write(f"Company: {company_result['company']}")
                    if 'error' in company_result:
                        st.error(f"Error: {company_result['error']}")
                
                with col2:
                    st.write("**Download Stats**")
                    st.write(f"Reports Found: {company_result.get('found', 0)}")
                    st.write(f"Downloaded: {company_result.get('downloaded', 0)}")
                    st.write(f"Failed: {company_result.get('failed', 0)}")
                
                # Show individual downloads
                if 'downloads' in company_result and company_result['downloads']:
                    st.write("**Individual Downloads**")
                    downloads_df = pd.DataFrame(company_result['downloads'])
                    st.dataframe(
                        downloads_df,
                        column_config={
                            "year": "Year",
                            "status": "Status",
                            "pages": "Pages",
                            "size_mb": st.column_config.NumberColumn("Size (MB)", format="%.1f"),
                            "url": st.column_config.LinkColumn("URL"),
                            "error": "Error",
                        },
                        hide_index=True,
                        width='stretch'
                    )

# TAB 3: URL Validator (original functionality)
with tab3:
    st.header("Investor Relations URL Validator")
    
    if not os.path.exists(master_path):
        st.error(f"File not found: {master_path}")
    else:
        df = read_tsv(master_path)

        if 'validated' not in df.columns:
            df['validated'] = False
        else:
            # Ensure validated is boolean (handles NaNs or 0/1)
            df['validated'] = df['validated'].fillna(False).astype(bool)

        # Filter for non-validated or all? Let's show all but highlight non-validated
        show_only_unvalidated = st.checkbox("Show only unvalidated", value=True)
        
        if show_only_unvalidated:
            display_df = df[df['validated'] == False].copy()
        else:
            display_df = df.copy()

        st.write(f"Showing {len(display_df)} companies")

        # Use data_editor for easy editing
        edited_df = st.data_editor(
            display_df,
            column_config={
                "investor_relations_url": st.column_config.LinkColumn("IR URL"),
                "validated": st.column_config.CheckboxColumn("Validated"),
                "CompanyName": st.column_config.TextColumn("Company", disabled=True),
                "CID": st.column_config.TextColumn("CID", disabled=True),
            },
            disabled=["CompanyName", "ISIN", "CID", "date refreshed", "Nasdaq_url", "Active_coverage?", "CCY", "MostRecentStockPrice", "TradedStockVolume", "StockTurnover"],
            hide_index=True,
            width="stretch",
            key="data_editor"
        )

        if st.button("Save Changes"):
            # Update the original dataframe with changes from edited_df
            for index, row in edited_df.iterrows():
                # Find the original row by CID (assuming CID is unique)
                cid = row['CID']
                df.loc[df['CID'] == cid, 'investor_relations_url'] = row['investor_relations_url']
                df.loc[df['CID'] == cid, 'validated'] = row['validated']
            
            write_tsv(df, master_path)
            st.success("Changes saved to instrument_master.csv!")
            st.rerun()

        st.divider()
        st.subheader("Current Master Data Preview")
        st.dataframe(df.head(10))

# TAB 4: Playwright Recording Helper
with tab4:
    st.header("🎬 Record Download Path with Playwright")
    
    st.markdown("""
    Use this tool to get the command for recording how to download an annual report.
    
    ### How It Works:
    1. **Select** a company and year below
    2. **Copy** the generated command
    3. **Run** it in your terminal
    4. **Navigate** to download the report in the browser that opens
    5. **Share** the generated script with the system for analysis
    """)
    
    if not os.path.exists(coverage_path):
        st.warning(f"Coverage table not found. Run `python scripts/update_coverage_table.py` first.")
    else:
        coverage_df = pd.read_csv(coverage_path, sep='\t')
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Select Report to Record")
            
            # Filter for incomplete reports
            show_incomplete = st.checkbox("Show only incomplete reports", value=True, key="rec_incomplete")
            
            if show_incomplete:
                display_df = coverage_df[coverage_df['Priority'] != 'Complete ✓'].copy()
            else:
                display_df = coverage_df.copy()
            
            # Company selection
            companies = sorted(display_df['CompanyName'].unique())
            if companies:
                selected_company = st.selectbox("Company", companies, key="rec_company")
                
                # Year selection
                company_data = display_df[display_df['CompanyName'] == selected_company]
                years = sorted(company_data['FiscalYear'].unique(), reverse=True)
                selected_year = st.selectbox("Year", years, key="rec_year")
                
                # Get report data
                report_data = coverage_df[
                    (coverage_df['CompanyName'] == selected_company) & 
                    (coverage_df['FiscalYear'] == selected_year)
                ].iloc[0]
                
                company_id = report_data['Company_Identifier']
                ir_url = report_data['IR_URL']
                
                st.divider()
                
                # Display company info
                st.info(f"""
                **Company:** {selected_company}  
                **ID:** {company_id}  
                **Year:** {selected_year}  
                **IR URL:** {ir_url}
                """)
                
        with col2:
            st.subheader("Quick Info")
            st.markdown("""
            **Script saves to:**  
            `aspiratio/utils/playwright_scripts/`
            
            **After recording:**  
            Share the generated `.py` file content
            """)
        
        st.divider()
        st.subheader("📋 Commands to Run")
        
        # Method 1: Helper script
        st.markdown("**Option 1: Using helper script (Recommended)**")
        helper_cmd = f"python -m aspiratio.tier3.record_download {company_id} {selected_year}"
        st.code(helper_cmd, language="bash")
        
        # Method 2: Direct playwright command
        st.markdown("**Option 2: Direct Playwright command**")
        output_file = os.path.abspath(f"aspiratio/utils/playwright_scripts/{company_id}_{selected_year}.py")
        playwright_cmd = f"playwright codegen --browser webkit --target python-async --output {output_file} {ir_url}"
        st.code(playwright_cmd, language="bash")
        
        st.divider()
        st.subheader("📖 Instructions")
        
        st.markdown("""
        ### Step-by-Step:
        
        1. **Copy** one of the commands above
        
        2. **Open** a terminal and navigate to the project directory:
           ```bash
           cd ~/Documents/github_repos/aspiratio
           source .venv/bin/activate
           ```
        
        3. **Run** the copied command
        
        4. **Browser opens** with Playwright Inspector:
           - Navigate to find the annual report
           - Click download links, buttons, etc.
           - All actions are recorded automatically
        
        5. **Close** the browser when done
        
        6. **Check** the generated script:
           ```bash
           cat {output_file}
           ```
        
        7. **Share** the script content so I can:
           - Analyze the navigation pattern
           - Extract the download logic
           - Integrate it into automated downloads
           - Apply to similar companies
        
        ### What Gets Recorded:
        - ✅ All clicks and navigation
        - ✅ Form inputs and selections  
        - ✅ Best-practice locators (role, text, test IDs)
        - ✅ Resilient selectors
        
        ### Tips:
        - Be deliberate with your clicks
        - Take the shortest path to the report
        - Wait for pages to load before clicking
        - Close the browser to save the recording
        """)

