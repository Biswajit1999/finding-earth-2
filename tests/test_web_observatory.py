from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_observatory_payload_matches_hashed_scientific_sources() -> None:
    payload_path = ROOT / "web/public/data/observatory.json"
    release_path = ROOT / "web/public/data/release.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    release = json.loads(release_path.read_text(encoding="utf-8"))

    assert release["observatory_sha256"] == hashlib.sha256(
        payload_path.read_bytes()
    ).hexdigest()
    assert release["source_count"] == len(payload["source_hashes"])
    for relative, expected in payload["source_hashes"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_observatory_preserves_scientific_labels_and_domains() -> None:
    payload = json.loads(
        (ROOT / "web/public/data/observatory.json").read_text(encoding="utf-8")
    )

    selection = payload["selection"]
    assert len(selection["cells"]) == selection["surface_grid"]["cells"] == 357
    assert {row["label"] for row in selection["cells"]} == {"MODEL-INFERRED"}
    assert payload["information_gain"]["row_count"] == len(
        payload["information_gain"]["rows"]
    )
    assert {row["label"] for row in payload["information_gain"]["rows"]} == {
        "SIMULATED"
    }
    assert payload["falsification"]["control_count"] == len(
        payload["falsification"]["controls"]
    )


def test_all_observatory_routes_exist_and_universe_hud_reserves_rows() -> None:
    routes = {
        "population",
        "selection",
        "climate",
        "stellar-environment",
        "atmospheres",
        "hwo",
        "missions",
        "information-gain",
        "model-sensitivity",
        "falsification",
        "evidence",
    }
    assert all((ROOT / "web/app" / route / "page.tsx").exists() for route in routes)

    universe = (ROOT / "web/components/universe/UniverseExplorer.tsx").read_text(
        encoding="utf-8"
    )
    assert "grid-rows-[minmax(0,1fr)_auto]" in universe
    assert 'data-testid="selected-system-panel"' in universe
    assert 'data-testid="discovery-history-controls"' in universe

