"""Validate published evidence without modifying analysis outputs."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (
    'scripts/evidence_catalog.py',
    'scripts/render_evidence_page.py',
    'scripts/profile_evidence_tables.py',
    'scripts/render_table_profiles.py',
)


def test_research_evidence_matches_the_repository_snapshot():
    result = subprocess.run(
        ['git', 'cat-file', '-e', 'HEAD:evidence/manifest.json'],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    ) if (ROOT / '.git').exists() else None
    option = '--check-committed' if result and result.returncode == 0 else '--check'
    for script in SCRIPTS:
        check = subprocess.run(
            [sys.executable, script, option], cwd=ROOT, text=True, capture_output=True, check=False,
        )
        assert check.returncode == 0, check.stdout + check.stderr
