#!/usr/bin/env python3
"""Analyze which reports are still missing."""
import pandas as pd
from collections import defaultdict

# Load validation results
v = pd.read_csv('validation_results.csv')
valid = v[v['Valid'] == True]

# All expected combinations
companies = pd.read_csv('instrument_master.csv')
years = [2019, 2020, 2021, 2022, 2023, 2024]

# Build expected set
expected = set()
for _, row in companies.iterrows():
    cid = row['Company_Identifier']
    for year in years:
        expected.add((cid, year))

# What we have
validated_set = set(zip(valid['CID'], valid['Year']))

# What's missing
missing = expected - validated_set

print(f'Total expected: {len(expected)}')
print(f'Validated: {len(validated_set)}')
print(f'Missing: {len(missing)}')
print()

# Group by company
by_company = defaultdict(list)
for cid, year in sorted(missing):
    by_company[cid].append(year)

print('Missing reports by company:')
for cid in sorted(by_company.keys()):
    years_missing = by_company[cid]
    name_row = companies[companies['Company_Identifier'] == cid]
    name = name_row['CompanyName'].iloc[0] if len(name_row) > 0 else cid
    print(f'  {name} ({cid}): {years_missing}')
