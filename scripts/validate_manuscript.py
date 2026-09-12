"""Static validation for the v2 manuscript when a TeX engine is unavailable."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate() -> list[str]:
    tex = (ROOT / "paper" / "main.tex").read_text(encoding="utf-8")
    macros = (ROOT / "paper" / "generated_results.tex").read_text(encoding="utf-8")
    bib = (ROOT / "paper" / "references.bib").read_text(encoding="utf-8")
    errors: list[str] = []
    required = [
        "Introduction", "Scientific Question", "Public Data", "Evidence Architecture",
        "Selection Function", "Population Model", "Habitable Zone", "Composition",
        "Stellar Environment", "Atmospheric Survival", "Observability", "Future Missions",
        "Bayesian Design", "Results", "Robustness", "Solar-System Falsification",
        "Limitations", "Discussion", "Conclusions",
    ]
    for section in required:
        if f"\\section{{{section}}}" not in tex:
            errors.append(f"missing section: {section}")
    if tex.count("{") != tex.count("}"):
        errors.append("unbalanced braces")
    if tex.count("\\begin{") != tex.count("\\end{"):
        errors.append("unbalanced environments")
    defined = set(re.findall(r"\\newcommand\{\\(\w+)\}", macros))
    used = set(re.findall(r"\\([A-Z][A-Za-z]+)", tex.replace(r"\\", "")))
    for name in sorted(used - defined):
        errors.append(f"undefined generated macro: {name}")
    bib_keys = set(re.findall(r"@\w+\{([^,]+),", bib))
    cited: set[str] = set()
    for group in re.findall(r"\\cite\{([^}]+)\}", tex):
        cited.update(key.strip() for key in group.split(","))
    for key in sorted(cited - bib_keys):
        errors.append(f"missing bibliography key: {key}")
    for figure in re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", tex):
        if not (ROOT / "paper" / "figures" / "v2" / figure).is_file():
            errors.append(f"missing figure: {figure}")
    return errors


if __name__ == "__main__":
    failures = validate()
    if failures:
        raise SystemExit("\n".join(failures))
    print("manuscript static validation: PASS")
