"""
Unit tests for name normalization and matching utilities.
"""
import pytest
from aspiratio.utils.name_match import normalize_name, match_rows

def test_normalize_name():
    assert normalize_name('ABB Ltd') == 'abb ltd'
    assert normalize_name('Hennes & Mauritz B') == 'hennes & mauritz b'
    # TODO: Add more normalization cases

def test_match_rows():
    # TODO: Add matching logic tests
    pass
