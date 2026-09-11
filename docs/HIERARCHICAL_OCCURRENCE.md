# Hierarchical occurrence inference

## Status

The likelihood and its expanded artificial-data validation are implemented and
the all-target real-data calculation has completed. See
[`DR25_OCCURRENCE.md`](DR25_OCCURRENCE.md) for the conditional fixed-box result,
its posterior-predictive checks and its model-family limitations.

All results in `results/population/validation/hierarchical_recovery.json` are
labelled **SIMULATED**. They are tests of the inference machinery, not
astronomical measurements.

## Estimand and likelihood

The initial population family is deliberately small and inspectable. For
orbital period `P`, planet radius `R`, slopes `alpha` and `beta`, and integrated
rate `F`, the intrinsic intensity per star is

```text
lambda(P,R) = F exp[alpha ln(P/365.25 d) + beta ln(R/R_earth)] / Z(alpha,beta)
```

per `d ln P d ln R`. `Z` is the analytic integral over the declared fitting
box. Therefore `F` is planets per selected star integrated over that exact box;
it is not the density at Earth and it is not a star-dependent habitable-zone
eta Earth.

For survey exposure `S(P,R)` in effective stars, the expected detected count is

```text
A(alpha,beta) F,
A(alpha,beta) = integral S(P,R) exp(alpha u + beta v) / Z dlnP dlnR.
```

The event likelihood is the inhomogeneous Poisson point-process likelihood.
The implementation uses a proper `Gamma(shape=0.5, rate=0.5)` prior for `F`
and independent `Normal(0, 2)` priors for the slopes. It integrates `F`
analytically conditional on each slope-grid point, then samples from the exact
conditional Gamma distribution. Gauss-Legendre integration is performed in
natural-log period and radius. Tests compare its normalization to the analytic
power-law integral.

## Uncertainty contract

The occurrence result uses multiple imputation rather than substituting a
fractional candidate count into a Poisson likelihood.

- One shared draw from the smooth false-alarm coefficient covariance produces
  correlated reliabilities for all candidates. Each is multiplied by the
  delivered astrophysical planet probability. The two candidates above the
  validated MES ceiling are evaluated as explicit lower and upper reliability
  scenarios; they are never extrapolated or silently dropped.
- Delivered asymmetric period and planet-radius errors are sampled, and every
  draw is tested against the estimand boundary. These radius intervals carry
  the archive's stellar-radius contribution, but the release will separately
  state that their cross-candidate stellar-systematics covariance is absent.
- The selection model is differentiated analytically with respect to its 11 MES,
  5 pipeline, and 5 conditional-vetting coefficients. The three published
  covariance blocks are propagated as independent blocks. The pipeline window
  coefficient fitted exactly at its non-negative boundary is held at zero;
  a symmetric Laplace draw through the forbidden region would be invalid.
- Positive selection draws use a local log-linear map from those derivatives.
  This captures fitted-coefficient uncertainty, not alternative model-family
  uncertainty. Regularization and wrong-completeness tests remain separate.

This is a two-stage posterior conditional on the released reliability and
selection models. A future fully generative model could instead fit planets,
instrumental false alarms, astrophysical false positives, injections and
observed TCEs jointly.

## Expanded synthetic validation

The deterministic release gate uses 60 independent replicates and 256
posterior imputations per replicate. Intended-recovery scenarios must satisfy
declared bias and coverage thresholds. Deliberately misspecified scenarios
must expose the expected failure rather than return a plausible-looking rate.

| Scenario | Relative rate bias | 95% coverage | Result |
|---|---:|---:|---|
| Flat population | -0.9% | 93.3% | Pass |
| Separable power law | +1.1% | 93.3% | Pass |
| Earth +/-20% period-radius box | +13.7% | 96.7% | Pass |
| 10% nominal completeness | +7.1% | 96.7% | Pass |
| Finite-injection uncertainty | +1.7% | 100.0% | Pass |
| Candidate reliability 0.65 | +0.1% | 98.3% | Pass |
| 18% log-radius uncertainty | +5.2% | 95.0% | Pass |
| Broken radius law fitted as one power law | +21.6% | 50.0% | Misspecification exposed |
| Completeness deliberately divided by two | +99.3% | 0.0% | Negative control exposed |

The broken-law result defines a real limitation of the initial model. The first
Kepler release must include slope-grid, prior, quadrature, radius-error and
alternative population-family sensitivity results alongside its baseline.

## Reproduce

```powershell
python.exe scripts/run_hierarchical_validation.py --root .
python.exe -m pytest tests/test_occurrence.py tests/test_hierarchical.py tests/test_hierarchical_validation.py -q
```

The JSON output contains the seed, scenario-generating parameters, perturbation
strengths, thresholds, bias, RMSE and coverage. The wrong-completeness case is
part of the required gate, so a code path that ignores selection cannot pass.
