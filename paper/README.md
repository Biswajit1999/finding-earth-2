# LaTeX manuscript

`main.tex` is the v2 publication manuscript. Every headline scientific value
is inserted from `generated_results.tex`, regenerated from committed JSON
products by:

```bash
python scripts/build_publication_release.py
```

Do not hand-edit the generated macro file.

## Compile

```bash
cd paper
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

The builder copies the verified project bibliography to `references.bib` and
copies publication figures to `figures/v2/`. When a TeX engine is unavailable,
run `python scripts/validate_manuscript.py` from the repository root for
structural, citation, figure, and generated-macro checks. Producing a PDF still
requires a TeX engine.
