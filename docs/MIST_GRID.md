# Compact MIST stellar-evolution grid

Status: **Phase 7 foundation**. This is a processed stellar-model product for
time-dependent habitable-zone inference. It is not an observed history of any
star.

The source is the official MIST v1.2 basic theoretical isochrone archive with
initial rotation `v/vcrit=0.4`. The 221,507,784-byte archive is pinned at
SHA-256 `bb3f42743f75676fa8bf6ca63c4cb2723a0839b77204efebcae39fa4610a92c8`.
The raw archive remains ignored; its source URL, retrieval time, version and
attribution are recorded in
`data/manifests/mist_v1p2_basic_isochrones.json`.

`scripts/prepare_mist_grid.py` streams the archive and selects MIST phase 0
only. It interpolates luminosity and effective temperature onto a fixed grid:

- 15 released metallicities from `[Fe/H]=-4.0` to `+0.5`;
- log10 age from 8.0 to 10.15 years in 0.05-dex steps;
- initial mass from 0.5 to 1.5 solar masses in 0.025-solar-mass steps.

Only masses supported by the phase-0 rows at each age and metallicity are
written. A 1.5-solar-mass star therefore has no artificial old-age
main-sequence continuation. The resulting 22,266 cells are committed under
`results/climate/` and hash-gated by the release invariant checker.

The next calculation will sample catalogue age, mass, metallicity, luminosity
and orbital uncertainties; interpolate only draws with complete grid support;
anchor each modeled luminosity history to the measured current luminosity; and
return broad `tau_HZ` and `f_CHZ` posteriors or `undetermined`. The grid alone is
not a continuous-habitability result.

Primary model references are Choi et al. (2016),
[doi:10.3847/0004-637X/823/2/102](https://doi.org/10.3847/0004-637X/823/2/102),
and Dotter (2016),
[doi:10.3847/0067-0049/222/1/8](https://doi.org/10.3847/0067-0049/222/1/8).
