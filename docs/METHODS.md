# Methods

Every equation implemented in this project, its citation, its stated validity
range, and the assumption it makes explicit rather than silent. This is the
Markdown companion to the interactive [Methods page](../web/app/methods) on
the website; the equations are identical.

## 1. Habitable-zone boundaries

**Reference:** Kopparapu et al. (2013), ApJ 765, 131,
doi:[10.1088/0004-637X/765/2/131](https://doi.org/10.1088/0004-637X/765/2/131),
with the **erratum** coefficients, ApJ 770, 82,
doi:[10.1088/0004-637X/770/1/82](https://doi.org/10.1088/0004-637X/770/1/82).

```
S_eff = S_eff,sun + a·T + b·T² + c·T³ + d·T⁴
T = T_eff − 5780 K
valid for 2600 K ≤ T_eff ≤ 7200 K

d = √(L / S_eff)   [au], L in solar luminosities
```

Five boundaries computed: recent Venus, runaway greenhouse, moist greenhouse,
maximum greenhouse, early Mars. **Conservative** HZ = runaway greenhouse to
maximum greenhouse. **Optimistic** HZ = recent Venus to early Mars. Reported
separately, never merged into a single boundary.

**Why the erratum, not the original table:** the arXiv v1 preprint of this
paper carries only the original (superseded) Table 3. The published
version-of-record contains both the original and a June 2013 erratum with
corrected coefficients. The two differ by more than a percent in
runaway-greenhouse S_eff for a Sun-like star (1.0512 vs. 1.0385), which shifts
the inner conservative habitable-zone edge and changes which planets qualify.
This project defaults to the erratum and implements both, so the effect of the
correction is measurable rather than assumed.

**Validity guard:** outside 2600–7200 K the model returns `NaN` (an explicit
"model does not apply" state), not a silently extrapolated value. Where an
extrapolated evaluation is still reported (e.g. for TRAPPIST-1 at 2566 K), it
is under a permanently attached `hz_model_extrapolated=True` flag.

Implementation: `src/earth2/habitability/hz.py`.

## 2. Earth Similarity Index (ESI)

**Reference:** Schulze-Makuch et al. (2011), Astrobiology 11(10), 1041–1052,
doi:[10.1089/ast.2010.0592](https://doi.org/10.1089/ast.2010.0592).

```
F_x = 1 − |(x − x₀) / (x + x₀)|

ESI_global = F_radius^(w_r/4) · F_density^(w_d/4)
           · F_escape_velocity^(w_v/4) · F_temperature^(w_t/4)

  w_r = 0.57, w_d = 1.07, w_v = 0.70, w_t = 5.58
```

This is computed in two tiers so `ESI_interior` and `ESI_surface` are
individually inspectable, not because `n=2` at the tier level changes the
final exponent:

```
ESI_interior = F_radius^(w_r/2) · F_density^(w_d/2)              (plain product --
ESI_surface  = F_escape_velocity^(w_v/2) · F_temperature^(w_t/2)  no further sqrt here)

ESI_global = √(ESI_interior · ESI_surface)   ← the one combining sqrt
```

which multiplies out to exactly the four-variable expression above. **An
earlier version of this implementation took an additional, incorrect square
root when forming `ESI_interior`/`ESI_surface`** (i.e. `√(F_r^(w_r/2) ·
F_d^(w_d/2))` instead of the plain product), which silently compounded to
`F_x^(w_x/8)` overall and systematically pushed every non-Earth score toward
1.0. It was caught by an external repository audit and fixed; regression
tests in `tests/test_habitability_esi.py` now check the vectorised
implementation against an independently coded flat evaluation of the
four-variable formula for the Solar System controls and 200 random parameter
draws, so a reappearance of this class of bug fails CI rather than shipping
silently (the previous test suite only checked loose bounds -- Earth = 1,
Venus > 0.9, Jupiter < 0.6 -- which the buggy exponent also satisfied).

**The temperature substitution:** the paper's fourth parameter is *surface*
temperature (Earth reference 288 K). Exoplanet catalogues supply only
*equilibrium* temperature, which excludes greenhouse warming by construction.
This project references the temperature term against Earth's own equilibrium
temperature (254 K, computed self-consistently from the same albedo
convention applied to every planet) rather than mixing the two conventions.
Because this substitution is a project-specific modification of the
published index, results in this repository should be cited as a *modified,
equilibrium-temperature* Earth Similarity Index, not as an unmodified
reproduction of Schulze-Makuch et al. (2011).

**The documented consequence:** Venus's high Bond albedo makes its equilibrium
temperature (232 K) *cooler* than Earth's. On this metric Venus scores 0.92 —
an Earth Similarity Index built from data that exists for real exoplanets
cannot separate a temperate rocky world from a runaway-greenhouse one. This is
a property of the available observations, verified by running Venus through
the identical pipeline as a labelled control, not asserted as a caveat
disconnected from the computation.

Implementation: `src/earth2/habitability/esi.py`.

## 3. Monte Carlo uncertainty propagation

Every parameter with a published asymmetric uncertainty is sampled from a
**two-piece (split) normal**:

```
x_sample = x + z·σ_upper   if z ~ N(0,1) > 0
x_sample = x + z·σ_lower   if z ≤ 0
```

4,000 draws per planet, fixed seed (20260824) for reproducibility.
Non-positive draws on positive-definite quantities (radius, mass, temperature)
are rejected and redrawn rather than clipped to zero, which would bias the
median upward for poorly constrained small planets. A parameter with a value
but no published uncertainty is sampled as a delta function and the omission
is counted (`mc_uncertainty_coverage`), feeding directly into the
observational-confidence score.

Implementation: `src/earth2/uncertainty/montecarlo.py`.

## 4. Rocky plausibility

**References:** Rogers (2015), ApJ 801, 41,
doi:[10.1088/0004-637X/801/1/41](https://doi.org/10.1088/0004-637X/801/1/41)
(1.6 R⊕ is where ~50% of Kepler planets stop being pure-rock density);
Fulton et al. (2017), AJ 154, 109,
doi:[10.3847/1538-3881/aa80eb](https://doi.org/10.3847/1538-3881/aa80eb)
(the 1.5–2.0 R⊕ radius valley).

```
p(rocky) = 1 / (1 + exp((R_p − 1.6) / 0.20))
```

A logistic, not a hard cut, spanning the observed valley the data actually
supports.

## 5. Characterisation metrics

**Reference:** Kempton et al. (2018), PASP 130, 114401,
doi:[10.1088/1538-3873/aadf6f](https://doi.org/10.1088/1538-3873/aadf6f).

```
TSM = S · (R_p³ · T_eq) / (M_p · R_star²) · 10^(−m_J/5)
S = 0.190 / 1.26 / 1.28 / 1.15 by radius bin

ESM = 4.29×10⁶ · (B_7.5(T_day)/B_7.5(T_star)) · (R_p/R_star)² · 10^(−m_K/5)
```

Kempton's T_eq is zero-albedo; this project's working `teq_used` assumes Bond
albedo 0.306, so the zero-albedo temperature is recomputed from insolation
specifically for this metric rather than substituted incorrectly. Undefined
(NaN) for non-transiting planets.

## 5a. Conservative habitability score

```
score_conservative_habitability = hz_conservative_prob · hz_teff_valid_fraction · p(rocky)
```

`hz_conservative_prob` is a Monte Carlo mean taken **conditional on** each
draw's sampled host effective temperature falling inside the Kopparapu
polynomial's stated 2600-7200 K validity range (Section 1); draws outside
that range are excluded rather than counted as "not habitable".
`hz_teff_valid_fraction` records what share of the posterior was actually
evaluable. For a host near or below the validity floor -- TRAPPIST-1 at
2566 K is the case this project's own uncertainty module names explicitly --
that conditioning can be severe: a confident-looking `hz_conservative_prob`
may be the mean of only a small minority of draws. Multiplying by
`hz_teff_valid_fraction` turns "100% HZ probability from 9% of evaluable
draws" into a score of roughly 0.09, which is what that evidence actually
supports, rather than letting the composite ranking read the conditional
probability as if it applied unconditionally. This is why TRAPPIST-1's
planets do not lead the current ranking despite very high Earth-similarity
scores -- see the "Top candidates" table in `README.md` and
`docs/LIMITATIONS.md`.

## 6. Composite Earth-2.0 index

```
index = exp( Σᵢ wᵢ · log(max(scoreᵢ, ε)) ),  Σwᵢ = 1,  ε = 0.01

Default weights: similarity 0.35, habitability 0.40,
                 confidence 0.25, characterisation 0.0
```

A **weighted geometric mean**, chosen because it is non-compensatory: a
near-zero component (e.g. zero habitable-zone membership) drags the whole
index toward zero regardless of how strong the other components are. Verified
in `tests/test_ranking.py::test_hot_jupiter_does_not_rank_highly_habitable`.

Implementation: `src/earth2/ranking/scores.py`.

## 7. Radial-velocity semi-amplitude and minimum mass

```
K = 28.4329 m/s · (Mp sin i / M_Jup) · ((M* + Mp)/M_sun)^(−2/3)
                · (P / 1 yr)^(−1/3) / √(1 − e²)
```

Inverted to recover M sin i from a fitted K. A three-criterion reliability
gate — at least 20 velocities, amplitude significance ≥3σ, residual scatter
below five times the fitted amplitude — must pass before a mass is reported;
see `docs/RESEARCH_NOTES.md` for the incident that made this gate necessary.

Implementation: `src/earth2/radial_velocity/rv.py`.

## 8. Physical constants

IAU 2015 Resolution B3 nominal solar/terrestrial conversion constants;
CODATA 2018 fundamental constants; Kopp & Lean (2011),
doi:[10.1029/2010GL045777](https://doi.org/10.1029/2010GL045777) for the
total solar irradiance value. Full table, each entry with its source, in
`src/earth2/constants.py`.
