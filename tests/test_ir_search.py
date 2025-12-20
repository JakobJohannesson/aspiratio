"""
Unit tests for IR URL search and validation helpers.
"""
from aspiratio.utils.ir_search import validate_ir_url

def test_validate_ir_url():
    assert validate_ir_url('https://global.abb/group/en/investors')
    assert validate_ir_url('https://www.ericsson.com/en/investors')
    assert not validate_ir_url('https://www.abb.com/about')
    # TODO: Add more cases
