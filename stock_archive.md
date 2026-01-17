# Stock Archive

Concise blueprint to recreate the OMXS30 annual-report acquisition pipeline (2019-2024) using the notebooks in `notebooks/` as the execution backbone. Coverage table (`coverage_table_updated.csv`) is the source of truth.

## Inputs & Outputs
- Inputs: [instrument_master.csv](instrument_master.csv), [omxs30_members.csv](omxs30_members.csv), [config.yaml](config.yaml)
- Tracking: [coverage_table_updated.csv](coverage_table_updated.csv) (TSV), [validation_results.csv](validation_results.csv)
- Artifacts: raw PDFs in `companies/{CID}/`, validated PDFs in `companies_validated/{CID}/`
- Logs/diagnostics: [agent_logs/runs](agent_logs/runs)

## Notebooks (run in order)
1. `notebooks/step1_Idenify_omxs30_companies.ipynb` — load OMXS30 list, reconcile with instrument master, seed missing rows in coverage table.
2. `notebooks/step2_Find_ir_pages.ipynb` — score IR URLs per company via [aspiratio/utils/ir_search.py](aspiratio/utils/ir_search.py).
3. `notebooks/step3_Find_annual_reports.ipynb` — enumerate candidate report URLs for 2019-2024 via [aspiratio/utils/report_downloader.py](aspiratio/utils/report_downloader.py) `find_annual_reports` and MFN fallback [aspiratio/tier1/mfn_search.py](aspiratio/tier1/mfn_search.py).
4. `notebooks/step4_Download_and_save_reports.ipynb` — download PDFs with `download_company_reports`, write to `companies/`, validate on the fly.
5. `notebooks/step5_Update_coverage_table.ipynb` — regenerate `coverage_table_updated.csv` from latest `download_summary_*.json` via [scripts/update_coverage_table.py](scripts/update_coverage_table.py).
6. `notebooks/step6_Retry_and_diagnose_failures.ipynb` — iterate incomplete rows, retry downloads, validate, and log reasons; uses [scripts/redownload_failed.py](scripts/redownload_failed.py) and diagnostics in [aspiratio/utils/report_downloader.py](aspiratio/utils/report_downloader.py).

## Core Workflow (CLI equivalents)
- Download missing: `aspiratio-download` (wraps [scripts/download_reports.py](scripts/download_reports.py))
- Validate PDFs: `aspiratio-validate` (wraps [scripts/validate_reports.py](scripts/validate_reports.py))
- Update coverage: `aspiratio-update` (wraps [scripts/update_coverage_table.py](scripts/update_coverage_table.py))
- Retry with fallbacks: `aspiratio-retry` (wraps [scripts/redownload_failed.py](scripts/redownload_failed.py))
- Diagnose connectivity: `aspiratio-diagnose`

## Conventions
- Target years: 2019–2024
- Coverage truth: `coverage_table_updated.csv` (TSV)
- Validation thresholds: 50–500 pages; require company + year mention (see [scripts/validate_reports.py](scripts/validate_reports.py))
- Exclusions: filter quarterly/SEC press content; prefer IR roots; MFN/Cision fallback for stubborn cases

## Re-run Checklist
- Ensure network access and `pip install -e .` plus `playwright install webkit` if Playwright needed
- Sync coverage first, then download, validate, update, retry
- Keep `download_summary_*.json` for audit; reruns read the latest summary

## Failure Handling
- Automatic retries with user-agent rotation and MFN fallback
- Playwright handlers for JS-heavy sites (see [aspiratio/utils/playwright_downloader.py](aspiratio/utils/playwright_downloader.py))
- Log every attempt in `agent_logs/runs/*.json`; annotate `Failure_Reason` in coverage table
