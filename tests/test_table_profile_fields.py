"""Exercise missing values, padded records and non-finite numeric tokens."""

from importlib import import_module
from pathlib import Path



def test_profiles_preserve_coverage_and_only_show_ranges_for_numeric_columns(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts'))
    profile_table = import_module('profile_evidence_tables').profile_table
    raw = b'flux,quality,temperature\n0.2,good,NaN\n,0,12\n1.4,bad\n'
    monkeypatch.setitem(profile_table.__globals__, 'read_bytes', lambda path, committed: raw)
    result = profile_table({'path': 'sample.csv', 'label': 'Sample', 'role': 'Data'}, False)
    flux, quality, temperature = result['columns']
    assert result['rows'] == 3
    assert result['width_mismatches'] == 1
    assert (flux['blank'], flux['minimum'], flux['maximum']) == (1, 0.2, 1.4)
    assert (quality['text'], quality['finite']) == (2, 1)
    assert 'minimum' not in quality
    assert (temperature['blank'], temperature['nonfinite'], temperature['finite']) == (1, 1, 1)
