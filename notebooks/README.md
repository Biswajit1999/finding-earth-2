# Reproducibility notebooks

Eight notebooks, one per pipeline stage, each calling the same `earth2`
functions the pipeline itself calls against the same committed `results/`
data everything else in this project reads. None of these recompute the
science a second, simplified way -- they call the real functions directly.

Run `python -m earth2 all` first if `results/` does not exist yet, then open
any notebook independently; they do not depend on each other.

| # | Notebook | Covers |
|---|---|---|
| 1 | [`01_data_acquisition_and_provenance`](01_data_acquisition_and_provenance.ipynb) | Where the 164,209-record scale claim comes from, manifest by manifest |
| 2 | [`02_crossmatch_and_mass_provenance`](02_crossmatch_and_mass_provenance.ipynb) | Mass-provenance classification; the Gaia DR3 exact-`source_id` crossmatch and the float64 precision trap it required guarding against |
| 3 | [`03_habitable_zone_model`](03_habitable_zone_model.ipynb) | The Kopparapu et al. (2013) flux-boundary model, the original-vs-erratum coefficient trap, and the TRAPPIST-1 validity-floor edge case |
| 4 | [`04_earth_similarity_index`](04_earth_similarity_index.ipynb) | The ESI itself, and a real exponent bug from this project's history reproduced numerically |
| 5 | [`05_monte_carlo_uncertainty`](05_monte_carlo_uncertainty.ipynb) | Split-normal sampling of asymmetric published uncertainties, propagated into ESI posteriors |
| 6 | [`06_composite_ranking`](06_composite_ranking.ipynb) | The non-compensatory geometric-mean ranking, the HZ-validity discount, and a weight-sensitivity check on the top 10 |
| 7 | [`07_transit_and_rv_validation`](07_transit_and_rv_validation.ipynb) | Transit-depth fitting validated against known planets; the RV reliability gate that stops a fit from fabricating a mass out of noise |
| 8 | [`08_results_and_case_studies`](08_results_and_case_studies.ipynb) | The headline scarcity result, a full case-study walkthrough, and why this project computes no probability of life |

Each notebook is committed with its outputs already executed, so it is
readable on GitHub without running anything -- but every number in it is
real: re-running the notebook against the same committed `results/`
reproduces it exactly (Monte Carlo cells use the project's fixed seed).
