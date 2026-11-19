from unittest.mock import patch

import pytest

from earth2.data_sources import base


def test_failed_cache_write_preserves_existing_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "RAW_DIR", tmp_path)
    destination = base.write_cache("source", b"old CSV contents\n")

    with patch.object(base.gzip.GzipFile, "write", side_effect=OSError("disk full")):
        with pytest.raises(OSError, match="disk full"):
            base.write_cache("source", b"new CSV contents\n")

    assert base.read_cache("source") == b"old CSV contents\n"
    assert list(tmp_path.iterdir()) == [destination]

    assert base.write_cache("source", b"new CSV contents\n") == destination
    assert base.read_cache("source") == b"new CSV contents\n"
