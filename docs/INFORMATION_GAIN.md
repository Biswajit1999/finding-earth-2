# Expected information gain

The information-gain lab asks one narrow question: **for this planet and this
declared measurement model, which supported action is expected to reduce a named
parameter uncertainty most?** It does not decide which planet deserves telescope
time and it does not estimate habitability.

## Definition

For parameters `theta`, current data `D`, action `a`, and as-yet unobserved result
`y`, the expected information gain is

`EIG(a) = E_y[KL(p(theta | D, y, a) || p(theta | D))]`.

The Phase 12 numerical release starts with a scalar Gaussian prior and the
explicit observation model `y = theta + epsilon`, where `epsilon` is independent
Gaussian noise. The conjugate solution is

`EIG = 0.5 ln(1 + sigma_prior^2 / sigma_observation^2)` nats,

and

`sigma_posterior = (sigma_prior^-2 + sigma_observation^-2)^-1/2`.

This limiting case is exact under those assumptions. Catalogue asymmetric errors
are reduced to the mean absolute split uncertainty only for this initial
experiment. That approximation cannot represent limits, multimodality, bounded
tails, or parameter covariance.

## Released synthetic actions

| Action | Parameter | Synthetic observation-noise requirement | Necessary current evidence |
|---|---|---|---|
| Mass precision | measured mass or retained `M sin i` | max(10% of value, 0.10 Earth masses) | finite two-sided catalogue uncertainty; mass prediction and upper limit rejected |
| Radius precision | planet radius | max(2% of value, 0.01 Earth radii) | finite two-sided uncertainty |
| Stellar-radius precision | stellar radius | max(1% of value, 0.005 Solar radii) | finite two-sided uncertainty |
| Stellar-age precision | stellar age | max(20% of value, 0.20 Gyr) | finite two-sided uncertainty |
| Eccentricity precision | eccentricity | sigma 0.03 | finite two-sided uncertainty; Gaussian result is only local because eccentricity is bounded |
| Inclination precision | inclination | sigma 0.5 degrees | finite two-sided uncertainty |

All 150 target-action rows are **SIMULATED** measurement-requirement experiments
for the leading 25 catalogue candidates. Eighty-three have the measured value and
two-sided uncertainty required by the model. Within-target ordering is conditional
on this exact menu and its deliberately visible precision requirements. It is not
an instrument forecast or observing proposal.

## Actions withheld from numerical ordering

- Ephemeris refinement needs a joint epoch-period posterior and covariance. A
  catalogue transit-midpoint error alone cannot predict a future transit window.
- XUV ranges in this project are physical scenarios, not calibrated posterior
  samples with an observation likelihood.
- A transmission-spectrum action needs a target-specific atmosphere forward
  model, wavelength-dependent throughput, clouds, covariance, and systematics.
- HWO accessibility uses generic architecture trade cases, so it cannot provide a
  validated direct-imaging likelihood.
- Albedo is currently a scenario prior, not an observational posterior.
- Atmospheric presence lacks a defensible target-specific prevalence prior,
  sensitivity, and false-positive rate.

These omissions are scientific results: the project refuses to produce precise
information values from an unrealistic generic instrument model.

## Cost and interpretation

Observing time and cost remain `not_modelled` on every row. The release does not
report information per unit time because it has no defensible target/instrument
exposure model. A high value means the synthetic likelihood is narrow relative to
the current catalogue uncertainty; it does not mean the requirement is feasible.

The implementation follows the expected-information framework introduced by
[Lindley (1956)](https://doi.org/10.1214/aoms/1177728069). The atmosphere-specific
boundary is informed by [Batalha & Line (2017)](https://arxiv.org/abs/1612.02085),
whose analysis shows why wavelength coverage, atmospheric assumptions, clouds,
and instrument noise must enter a spectral information calculation.

## Reproduction

Run `python scripts/build_information_gain.py`. The source catalogue hash, action
definitions, observation models, output hashes, and unsupported-action reasons are
stored in `results/information_gain/`.
