"""
Utility functions for reading and writing TSV files with thousands separators.
"""
import pandas as pd

def read_tsv(path: str) -> pd.DataFrame:
    """Read a TSV file, handling thousands separators in numeric columns."""
    # TODO: Implement robust TSV reading
    return pd.read_csv(path, sep='\t')

def write_tsv(df: pd.DataFrame, path: str) -> None:
    """Write a DataFrame to TSV."""
    df.to_csv(path, sep='\t', index=False)
