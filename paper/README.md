# LaTeX manuscript

`main.tex` is the publication-format companion to this repository: the same
methodology and results as the website's long-form research article and
`docs/METHODS.md`, set as a standard two-column research paper with numbered
figures, a verified bibliography, and no LaTeX distribution beyond a stock
TeX Live or MiKTeX install.

## Compiling

```bash
cd paper
pdflatex main
bibtex main
pdflatex main
pdflatex main
```

Two `pdflatex` passes after `bibtex` are required (standard for any
`natbib`-based document) so that citation numbers and the bibliography settle.
No package beyond a standard distribution is needed: `amsmath`, `amssymb`,
`graphicx`, `booktabs`, `caption`, `hyperref`, `natbib`, `xcolor`, `times`,
`geometry` are bundled with every mainstream TeX distribution.

## Regenerating the figures

The figures in `figures/` are title-less variants of the ones in
`../results/figures/`: a journal figure gets its label from the
`\caption{}` set underneath it by LaTeX, so an in-image title would repeat
that label a second time in a different font. Regenerate them with:

```bash
python ../scripts/generate_paper_figures.py
```

which reads `../results/analysis_catalogue.parquet` (run
`python -m earth2 analyse` first if it does not exist) and writes into this
directory's `figures/` subfolder.

## Bibliography

`main.tex` references `../references/references.bib` directly rather than a
local copy, so the manuscript always cites from the same, single verified
bibliography the rest of the project uses -- no risk of the two drifting
apart.

## Validation performed without a local LaTeX installation

This manuscript was written and checked without a LaTeX compiler available
in the authoring environment. Before being committed, it was validated with
a small script (not part of the package, since a real `pdflatex` run
supersedes it) that checks: brace balance; `\begin`/`\end` environment
pairing; every `\cite`/`\citep`/`\citet` key resolves in the `.bib` file;
every `\includegraphics` path exists on disk; every `\ref`/`\eqref` target
has a matching `\label`; and every table row's cell count matches its
declared column specification. If you find a compilation issue despite
this, please open an issue -- it was not caught by inspection alone.
