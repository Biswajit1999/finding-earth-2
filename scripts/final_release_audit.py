"""Machine-check the Phase 16 scientific release gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def exists(path: str) -> bool:
    return (ROOT / path).is_file()


def audit() -> dict[str, Any]:
    summary = read("results/analysis_summary.json")
    dr25 = read("results/population/dr25_summary.json")
    occurrence = read("results/population/dr25_occurrence_posterior.json")
    story = read("results/population/dr25_observed_vs_intrinsic.json")
    composition = read("results/composition/bulk_composition_ensemble.json")
    climate = read("results/climate/continuous_hz.json")
    environment = read("results/environment/xuv_escape_scenarios.json")
    atmosphere = read("results/atmosphere/atmosphere_evidence.json")
    hwo = read("results/hwo/hwo_precursor_atlas.json")
    missions = read("results/missions/mission_observatory.json")
    info = read("results/information_gain/information_gain.json")
    falsification = read("results/falsification/falsification_summary.json")
    release = read("earth2-v2-data-release/release_inventory.json")
    gates = {
        "v1 preserved": exists("docs/V2_BASELINE_AUDIT.md") and exists("paper/figures/hz_diagram.png"),
        "literature audit": exists("docs/LITERATURE_V2.md"),
        "evidence graph": exists("docs/EVIDENCE_MODEL.md") and exists("results/evidence/summary.json"),
        "Kepler completeness": dr25["injections_all"] == 146294,
        "selection validation": exists("results/population/validation/hierarchical_recovery.json"),
        "population inference": occurrence["release_status"].startswith("conditional_fixed_box"),
        "observed versus intrinsic": story["label"] == "OBSERVED + MODEL-INFERRED",
        "explicit occurrence definition": "estimands" in occurrence,
        "composition ensemble": len(composition["records"]) == 3852,
        "stellar evolution": climate["population"]["inferred"] == 815,
        "climate sensitivity": climate["population"]["classification_robustness"]["boundary_or_model_sensitive"] == 16,
        "stellar environment": environment["population"]["with_escape_ensemble"] == 43,
        "atmosphere scenarios": atmosphere["observability"]["supported"] == 54,
        "modern spectrum architecture": atmosphere["spectrum_evidence"]["reduction_count"] == 1826,
        "HWO catalogue": hwo["catalogue"]["hpic_rows"] == 12944,
        "direct imaging posterior": hwo["sampling"]["draws_per_target"] == 512,
        "mission observatory": len(missions["missions"]) == 6,
        "information gain": info["supported_rows"] == 83,
        "Solar-System falsification": falsification["venus_conservative_hz_probability"] == 0,
        "model sensitivity": exists("results/falsification/candidate_model_sensitivity.csv"),
        "frozen release": release["file_count_before_inventory"] >= 60,
        "manuscript": exists("paper/main.tex") and exists("paper/generated_results.tex"),
        "README v2": "catalogue is not the Universe" in (ROOT / "README.md").read_text(encoding="utf-8"),
        # `web/out` is intentionally untracked and is built in the independent
        # frontend CI job. The Python audit verifies the committed inputs and
        # export validator; that job then proves the actual static output.
        "website export": all(
            exists(path)
            for path in (
                "web/app/page.tsx",
                "web/app/beyond/page.tsx",
                "web/app/perspective/page.tsx",
                "web/public/data/release.json",
                "web/scripts/check-static-export.mjs",
            )
        ),
        "source scale": summary["scale"]["total_source_records"] == 164209,
    }
    failed = [name for name, passed in gates.items() if not passed]
    manifest_ok = True
    for line in (ROOT / "earth2-v2-data-release" / "MANIFEST.sha256").read_text().splitlines():
        expected, rel = line.split("  ", 1)
        actual = hashlib.sha256((ROOT / "earth2-v2-data-release" / rel).read_bytes()).hexdigest()
        manifest_ok &= actual == expected
    gates["release checksums"] = manifest_ok
    if not manifest_ok:
        failed.append("release checksums")
    return {
        "schema_version": "1.0",
        "label": "RELEASE-AUDIT",
        "release": "2.1.1",
        "gate_count": len(gates),
        "passed": len(gates) - len(failed),
        "failed": failed,
        "gates": gates,
    }


if __name__ == "__main__":
    result = audit()
    output = ROOT / "results" / "final_release_audit.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if result["failed"]:
        raise SystemExit(1)
