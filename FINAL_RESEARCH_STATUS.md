# Finding Earth 2.0 v2 — final research status

**Release:** 2.0.0  
**Scientific status:** complete for the declared v2 scope; conditional inference,
not a discovery or probability of life  
**Audited source checkpoint:** `01f943344ea1ef66c28de566a656ad3abb6b94e1`  
**Website:** <https://biswajit1999.github.io/finding-earth-2/>  
**Author:** Biswajit Jana

## 1. Scientific questions addressed

The project asks what humanity detected, what Kepler could detect, what
period-radius population is consistent with those observations, how conclusions
change across physical models, and which supported observation should reduce
uncertainty most. It does not ask the available data to establish life.

## 2. Exact datasets used

NASA Exoplanet Archive `ps`, `pscomppars`, `stellarhosts`, TOI, Kepler KOI,
Kepler TCE, K2 candidates, microlensing, transit spectra, emission spectra,
spectrum index, and direct-imaging stars; exact Gaia DR3 source-ID crossmatches;
Kepler DR25 stellar, injection and recovered/vetted products; pinned
KeplerPORTs validation files; MIST v1.2 basic isochrones; MAST MUSCLES and
Mega-MUSCLES SEDs; HPIC v1.1 plus separate TSS25 membership; mission-source
records; and public MAST/DACE products for supported deep dives. Query, version,
URL, retrieval time, delivered rows, and SHA-256 live in `data/manifests/` and
the method documents.

## 3. Total source records

The v1 archive funnel contains **164,209** provenance-tracked source records
across 13 retrievals. DR25 completeness products are a separate artificial-signal
experiment and are not added to that headline for vanity scale.

## 4. Unique physical entities

The confirmed catalogue has **6,354 exoplanets around 4,764 host systems**.
Five Solar-System controls remain outside those counts. The evidence graph
indexes 89,073 measurement records and 89,131 measurement-publication links.

## 5. Completeness data volume

The DR25 foundation contains 200,038 stellar rows, 146,294 injections, and
45,377 recovered TCE-vetting rows. The fixed contract selects 114,105 stars,
84,556 injections, 30,012 recoveries, and 26,219 vetted planet candidates.
No injection lacks a stellar match; 29,549 selected stars have no injection and
are handled by the validated target-aware selection model.

## 6. Observed candidate result

The observed search finds **174** nominal conservative-HZ planets, **15** also
below 1.6 Earth radii, and **1** of those with an independently measured mass.
This is catalogue scarcity among detected and confirmed planets, not cosmic
rarity.

## 7. Intrinsic population result

For Kepler DR25 GK dwarfs in the fixed 50–500 day and 0.5–2 Earth-radius box,
the conditional Poisson model gives **0.692 planets per selected star**, with a
95% interval of **0.267–1.918**. Eighty-nine observed candidates imply about 54
latent valid candidates and 78.3 shape-weighted effective stars.

## 8. Eta-Earth definition and posterior

No universal $\eta_\oplus$ is claimed. The released equivalent estimands state
their exact domains: the full fixed box above has 0.692
(0.267–1.918); the Hsu-like 237–500 day, 0.75–1.5 Earth-radius projection has
median **0.122**; and the Bryson-like Earth ±20% box (292.2–438.3 days,
0.8–1.2 Earth radii) has median **0.041**. These are period-radius projections
for the selected stellar population, not HZ- or biology-defined rates.

## 9. Strongest candidate evidence

Proxima Cen b leads the legacy composite at 0.876, with strong bulk similarity
and nearby observability, but its mass is $M\sin i$. GJ 1061 d is the strongest
leading example with an accepted measured-mass class. The project deliberately
does not name a universally “best planet”; evidence vectors and Pareto views
show different strengths.

## 10. Evidence against simplistic ranking

Venus reaches ESI **0.874** despite a hostile surface. Composition models show
a median probability span of **0.251** where all three apply. Earth-pivot Kepler
selection is only **0.00198%**. Together these results defeat the ideas that a
similarity score is habitability, a radius fixes composition, or a catalogue is
an unbiased population.

## 11. Climate-model sensitivity

Of 6,354 confirmed planets, 815 support time-dependent MIST-anchored inference.
Twenty-two remain inside across implemented boundary prescriptions; 16 are
boundary- or model-sensitive. Unsupported ages and stellar tracks remain
`undetermined` rather than being filled with confident classifications.

## 12. Stellar-environment findings

Among 60 high-value terrestrial-size targets, 46 support bounded activity
histories, 43 support 27-case energy-limited escape ensembles, and nine use
exact-host MUSCLES SEDs. These are model scenarios with fixed planet properties,
not evidence that an atmosphere survived.

## 13. HWO precursor findings

HPIC v1.1 contributes 12,944 stars; 12,682 support EEID geometry and 12,405
support Kopparapu HZ geometry. The exact known-planet crossmatch finds 744
planets on 464 HPIC hosts, with 694 supporting imaging scenarios. The 512-draw
results use three generic instrument concepts, not a final HWO design or yield.

## 14. Expected-information-gain findings

Six actions were evaluated for 25 candidates. Eighty-three of 150 rows pass
their uncertainty and likelihood contracts. Under the declared Gaussian
experiment, improving the stellar radius of Kepler-296 f is the largest supported
action at **3.94 bits**. Observing cost and time are not modelled, so this is not
an observing-program priority per hour.

## 15. Solar-System falsification

Venus falsifies ESI-as-habitability; Mars falsifies HZ-membership-as-surface
climate. Earth confirms expected terrestrial-envelope behavior. Mercury and
Jupiter exercise unsupported-domain handling. Controls never enter exoplanet
counts or ranks.

## 16. Failed hypotheses

Synthetic tests reject the idea that raw detections recover intrinsic rates.
A deliberately halved completeness surface produces large bias. A broken-radius
population exposes misspecification in the simple power-law family. Solar-System
controls reject similarity and HZ position as sufficient habitability classifiers.

## 17. Unavailable data

Gaia DR4, PLATO science data, Roman survey science, ANDES observations, and HWO
observations are unavailable as of the mission snapshot and are never labelled
observed. Complete target-specific XUV histories, atmospheric retrieval
likelihoods, ephemeris covariances, and observing-time cost models are also
unavailable for much of the candidate set.

## 18. Model-dependent results

Occurrence, reliability, rocky probabilities, continuous-HZ histories, escape,
scale heights, direct-imaging access, mission forecasts, and information gain
all depend on declared models or scenarios. Their labels and support limits are
retained in machine-readable outputs; they are never multiplied into a
probability of habitability.

## 19. Reproducibility commands

```bash
python -m earth2 report
python scripts/check_release_invariants.py
python scripts/build_publication_release.py
python scripts/validate_manuscript.py
python scripts/final_release_audit.py
pytest -q
ruff check src tests notebooks scripts
mypy src/earth2
cd web && npm ci && npm run typecheck && npm run lint && npm run build
```

## 20. Test results

The final local release run passes **287 Python tests**, Ruff, mypy across 75
source files, 67 scientific release invariants, manuscript validation, 26 core
audit gates, TypeScript, ESLint, a 6,388-page Next build, 6,387 exported HTML
files, 35 export templates, and desktop/mobile browser QA with zero HUD overlap
or horizontal overflow. The post-v2 physics calculator adds five tests.

## 21. Website URL

<https://biswajit1999.github.io/finding-earth-2/>

## 22. Release version

Software, website, manuscript, and data bundle are version **2.0.0**. The Zenodo
deposit is prepared; its DOI is `pending` until minted and is not fabricated.

## 23. Git commit SHA

The publication bundle records source checkpoint
`d1772672e0c85ac2690016de71fde19c112f7efb`; the fully audited Phase 15 checkpoint
is `01f943344ea1ef66c28de566a656ad3abb6b94e1`. The signed release reference is
the repository's `v2.0.0` tag, created only after this final audit commit.

## 24. Highest-value next scientific experiment

Under the supported EIG prototype, improve **Kepler-296 f's stellar radius**.
The next methodological upgrade should add realistic observing cost and a joint
stellar/planet posterior before treating that result as a scheduling decision.
