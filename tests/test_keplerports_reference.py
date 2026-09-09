import hashlib
import json

import pytest

from earth2.population.keplerports_reference import validate_reference


def test_reference_validation_fails_closed_on_missing_or_changed_files(tmp_path):
    reference = tmp_path / "reference"
    reference.mkdir()
    payload = b"official fixture"
    (reference / "one.dat").write_bytes(payload)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "repository": "https://github.com/nasa/KeplerPORTs",
                "commit": "a" * 40,
                "files": {"one.dat": hashlib.sha256(payload).hexdigest()},
            }
        )
    )
    with pytest.raises(ValueError, match="Incomplete"):
        validate_reference(reference, manifest)
    files = {f"input-{i}.dat": hashlib.sha256(payload + bytes([i])).hexdigest() for i in range(6)}
    manifest.write_text(
        json.dumps(
            {
                "repository": "https://github.com/nasa/KeplerPORTs",
                "commit": "a" * 40,
                "files": files,
            }
        )
    )
    with pytest.raises(FileNotFoundError, match="Missing"):
        validate_reference(reference, manifest)
    for i, name in enumerate(files):
        (reference / name).write_bytes(payload + bytes([i]))
    validate_reference(reference, manifest)
    (reference / "input-2.dat").write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_reference(reference, manifest)
