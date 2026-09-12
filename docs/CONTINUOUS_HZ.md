# Time-dependent habitable-zone inference

Status: **Phase 7 model release**. Every numerical result is
**MODEL-INFERRED**. It is an incident-flux history under named stellar and
climate models, not an observation of a planet's past climate and not evidence
for surface liquid water, an atmosphere, biology or life.

## What changed

The instantaneous habitable-zone flag asks whether a planet is inside a chosen
flux interval today. This release also asks how long the planet's fixed orbit
occupied that interval while its host evolved along the main sequence:

\[
\tau_\mathrm{HZ}=\int I[S_\mathrm{outer}(t) < S_p(t) < S_\mathrm{inner}(t)]\,dt,
\qquad
f_\mathrm{CHZ}=\tau_\mathrm{HZ}/t_\star.
\]

`src/earth2/climate/evolution.py` trilinearly interpolates the committed MIST
v1.2 phase-0 grid in age, initial mass and metallicity. Each posterior stellar
track is shifted in log luminosity so its current epoch exactly matches the
sampled catalogue luminosity. The planet's orbit is held fixed; migration,
eccentric-season climate, atmospheric evolution and pre-main-sequence exposure
are outside this calculation.

The integration begins at 0.1 Gyr, the earliest age in the released compact
grid. The unavailable earlier interval is not counted as habitable, while the
reported fraction still divides by the sampled stellar age. This choice is
conservative and especially material for young systems.

## Evidence gate

All central values and asymmetric uncertainties for stellar age, mass,
metallicity, log luminosity and semimajor axis must be finite. An age is treated
as effectively unconstrained when either side of its reported uncertainty is
larger than 75% of the central age or its 68% interval exceeds 6 Gyr. At least
half of posterior draws must remain inside the MIST phase-0 grid. A system that
fails any gate is reported as `undetermined`; it does not silently become an
out-of-HZ system.

The catalogue contains 1,947 records with all required central values and error
columns. Strict age precision and continuous MIST support leave 815 inferred
histories. Of the remaining records, 4,407 lack a required value, 635 have an
effectively unconstrained age, 420 lack present-day MIST support, 49 lack a
continuous supported track and 28 are invalid or younger than the modeled
start. These are evidence outcomes, not failed attempts to force a result.

## Climate-boundary sensitivity

Three published Kopparapu et al. (2013) prescriptions are kept separate:

| Prescription | Inner boundary | Outer boundary | Interpretation |
|---|---|---|---|
| conservative | runaway greenhouse | maximum greenhouse | classical 1D climate limits |
| moist greenhouse | moist greenhouse | maximum greenhouse | stricter water-loss inner edge |
| optimistic empirical | recent Venus | early Mars | empirical Solar-System limits |

For every supported planet the product reports the present-day membership
probability, posterior quantiles for `tau_HZ` and `f_CHZ`, the spread among
prescriptions, and a robust-inside / robust-outside / sensitive classification.
These alternatives test boundary choice inside one published 1D framework.
They are not three independent general-circulation models, and the product says
so rather than overstating model diversity.

## Reproduction

```powershell
python.exe scripts/build_continuous_hz.py
python.exe -m pytest tests/test_climate_evolution.py
python.exe scripts/check_release_invariants.py
```

The deterministic CSV, JSON, PNG and SVG outputs live in `results/climate/` and
are hash-gated by `continuous_hz_products.json`.

## Primary references

- Choi et al. (2016), MIST isochrones, doi:10.3847/0004-637X/823/2/102.
- Dotter (2016), MIST interpolation framework,
  doi:10.3847/0067-0049/222/1/8.
- Kopparapu et al. (2013), habitable-zone flux boundaries,
  doi:10.1088/0004-637X/765/2/131 and erratum
  doi:10.1088/0004-637X/770/1/82.
