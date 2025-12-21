import streamlit as st
import pandas as pd
import os
import sys

# Ensure repo root is in sys.path for aspiratio imports
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from aspiratio.utils.io import read_tsv, write_tsv

st.set_page_config(page_title="IR URL Validator", layout="wide")

st.title("Investor Relations URL Validator")

master_path = os.path.join(repo_root, 'instrument_master.csv')

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



