# Synthetic selection-function validation

## Status and scope

**Evidence label: SIMULATED.** This experiment is a controlled software and
inference validation. It is not a measurement of the Kepler population, an
estimate of eta-Earth, or evidence that any planet is habitable.

The purpose is to test a release gate before real population inference: when the
true occurrence rate and complete selection function are known, does the count
likelihood recover the injected rate with calibrated uncertainty?

## Declared synthetic survey

Each of 300 deterministic replicates contains 10,000 Sun-like targets. The
injected population has a Poisson mean of 0.7 planets per star over:

- orbital period 10–400 days, with `dN/dln(P) proportional to P^0.3`;
- radius 0.7–2.0 Earth radii, with
  `dN/dln(R) proportional to R^-0.8`;
- a 1,460-day observing baseline and 0.9 duty cycle.

The scenario selection probability is the product of four independently named
terms:

1. circular Sun-like transit geometry;
2. a Poisson observing-window probability for at least three transits;
3. a logistic pipeline-recovery curve in synthetic multiple-event statistic;
4. a separate logistic vetting factor.

The mean selection is integrated by Gauss–Legendre quadrature under the declared
intrinsic period-radius distribution. Detected synthetic planets are drawn with
that same selection. A Poisson count likelihood with known exposure and a
Jeffreys prior yields the posterior for occurrence.

These functions deliberately simplify the real Kepler problem. They omit target
heterogeneity, measurement error, false alarms, reliability uncertainty,
multi-planet dependence, astrophysical multiplicity and selection-calibration
uncertainty. Those effects must enter the real model or its sensitivity analysis.

## Acceptance tests

The deterministic run must satisfy all of these conditions:

- absolute relative bias below 3%;
- empirical coverage between 90% and 99% for nominal 95% intervals;
- omitting transit geometry produces a clearly incorrect occurrence estimate;
- changing the assumed period-radius population changes the integrated
  selection by more than 10%, demonstrating proposal dependence;
- invalid domains, non-finite exposure and insufficient replicate counts fail
  closed.

## Results

| Diagnostic | Result |
|---|---:|
| Injected occurrence | 0.7000 planets per star |
| Mean selection probability | 0.0124110 |
| Mean detected count | 86.9767 |
| Mean selection-aware posterior estimate | 0.704830 |
| Relative bias | +0.6901% |
| RMSE | 0.074053 planets per star |
| Nominal interval mass | 95% |
| Empirical coverage | 94.6667% |
| Raw detected planets per star | 0.00869767 |
| Geometry-omitted posterior estimate | 0.0128705 |
| Flat-log proposal mean selection | 0.0168027 |
| Skewed proposal mean selection | 0.00464980 |
| Proposal relative difference | -72.3271% |

The selection-aware estimator passes the declared bias and coverage gates. The
raw detected fraction is about eighty times smaller than the injected population
rate, while the geometry-omitted calculation also fails badly. These are
intentional negative controls: a count cannot be interpreted without the same
survey definition and selection factors used to form its exposure.

The proposal sensitivity is also material. The detection probability is averaged
over the intrinsic period-radius distribution, so that population shape cannot be
silently borrowed from the injection proposal. The real inference must estimate
shape and normalisation together or publish sensitivity to defensible alternatives.

## Reproduction

From the repository root:

```powershell
python.exe scripts/run_selection_validation.py --root .
python.exe -m pytest tests/test_synthetic_selection.py -q
```

The committed JSON artifact is
`results/population/synthetic_selection_validation.json`. Two consecutive runs
with seed 726381 produced the identical SHA-256:

```text
a61b68c726efda84b9ca306c9f635e20abe2f563ad5b5324cf9bb20178fc92db
```

The implementation is intentionally separate from the official DR25 products.
Phase 4 may use this validated likelihood structure only after replacing every
synthetic survey term with a documented Kepler target sample, calibrated
completeness and reliability treatment.
