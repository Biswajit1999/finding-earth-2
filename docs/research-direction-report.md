# Finding Earth 2.0: Research Direction and Publication Readiness

**Prepared for:** Biswajit Jana  
**Assessment date:** 29 August 2026  
**Scope:** scientific positioning, 3D visualisation, selection effects, article quality, and a practical route to public peer feedback

## Executive decision

Finding Earth 2.0 should not compete with NASA by becoming another catalogue browser. NASA Eyes on Exoplanets already provides a scientifically accurate 3D tour of thousands of planetary systems. The stronger and more defensible identity is:

> **A selection-aware exoplanet cartography and candidate-evidence observatory: a reproducible interface for asking how the confirmed sample was discovered, where each method reaches, how measurement quality changes candidate rankings, and where the evidence stops.**

The project already has the difficult foundations: a reproducible multi-archive pipeline, uncertainty propagation, separable ranking axes, Gaia crossmatching, per-measurement source links, deep dives, and real 3D positions. The recommended upgrade is to connect those parts around testable questions rather than add decorative realism.

The first upgrade is now implemented: the 3D Universe can replay discoveries from 1992 to 2026 while retaining distance and method filters. It explicitly states that this is archive chronology, not stellar motion. The Galaxy view now uses a true camera crop around the Sun and collision-free method-shell labels.

## What is already original enough to be worth sharing

The catalogue itself is not novel; the NASA Exoplanet Archive is the authoritative source. A photorealistic planet or galaxy is not a scientific contribution either. The project becomes distinctive through the combination of:

1. **Evidence-aware ranking.** Physical similarity, conservative-habitable-zone placement, observation quality, and characterisation potential remain separate and inspectable.
2. **Selection-aware spatial interpretation.** The interface treats the discovered sample as the footprint of instruments and surveys, not as the underlying Galactic planet population.
3. **Discovery history in 3D.** Users can see the sample accumulate by year and then isolate the method responsible for each spatial pattern.
4. **Traceable measurements.** A displayed value can be followed to its archive query or publication source, without exposing implementation jargon in the public navigation.
5. **Explicit negative results.** Missing masses, out-of-domain habitable-zone calculations, unavailable time series, and absent distances are reported rather than silently imputed.

This is best described as an exploratory research instrument and a reproducible research communication project. It is not yet a corrected measurement of exoplanet occurrence across the Milky Way.

## Why the spatial map must be interpreted cautiously

The current 3D export contains 6,327 systems with measured distances and discovery years from 1992 through 2026. The growth is strongly non-uniform: 46 systems were in the record by 2000, 497 by 2010, 1,938 by 2015, 4,325 by 2020, and 6,327 by 2026.

The methods occupy visibly different volumes:

| Detection method | Systems | Median host distance | Maximum in this snapshot |
|---|---:|---:|---:|
| Transit | 4,673 | 475 pc | 8,500 pc |
| Radial velocity | 1,199 | 44 pc | 1,540 pc |
| Microlensing | 281 | 6,200 pc | 8,340 pc |
| Imaging | 92 | 95 pc | 230 pc |
| Transit timing variations | 42 | 399 pc | 1,315 pc |

These are empirical properties of this archive snapshot, not instrument sensitivity limits. The contrast is especially clear toward the Galactic centre: 98.6% of microlensing detections are within 10 degrees of Sagittarius A*, compared with 0.1% of transits and 1.3% of radial-velocity detections. That is primarily survey geometry. The K2 Campaign 9 microlensing programme, for example, deliberately observed a compact field toward the Galactic bulge.

This caution is supported by published analysis. Maliuk and Budaj found that several apparent Kepler-plus-Gaia spatial gradients became statistically insignificant after correcting observational bias. Foreman-Mackey, Hogg, and Morton likewise show why population inference from planet catalogues must account for non-trivial selection effects, detection efficiency, and noisy measurements.

Therefore the map should use the language **“discovered sample,” “archive record,” “survey footprint,” and “empirical reach.”** It should not use **“planet density,” “Galactic occurrence,” or “where planets are common”** unless a selection-function model and surveyed-star denominator have been added.

## Is realistic 3D animation possible?

Yes, with an important definition of realistic.

### Scientifically realistic

- positions derived from right ascension, declination, and measured distance;
- a clearly named heliocentric coordinate frame;
- explicit log-radius compression, with a future linear/log toggle;
- discovery-year playback with method and distance filters;
- uncertainty or quality encoding based on Gaia astrometry;
- schematic Milky Way context clearly separated from measured host positions;
- pause, step, reset, keyboard controls, and reduced-motion support.

### Visually realistic but scientifically weak

- imagined surfaces for planets whose atmospheres and surface conditions are unknown;
- an exterior photographic Milky Way presented as measured geometry;
- rapid “stellar motion” over the 1992-2026 discovery interval;
- cinematic travel that hides coordinate compression or changes scale without disclosure.

Gaia supports epoch propagation using an astrometric model, so true proper-motion animation could be built later. Over a few decades, however, the physical movement of most catalogue stars is too small to explain the changing discovery map. Exaggerating it would need a separate timescale, vector scale, covariance propagation, and a prominent label. Discovery chronology is both more honest and more relevant to the research question.

The existing WebGL point-cloud design is technically adequate. Six thousand points are well below the scale at which complex level-of-detail architecture is needed. Instancing becomes valuable only if points are replaced with many repeated meshes. The current priority should be interpretation, accessibility, and analytical controls.

## A proper research programme

### Study 1 - Method footprints in Galactic coordinates

**Question:** Do detection methods occupy statistically distinguishable sky and distance distributions?

**Null hypothesis:** after conditioning on survey epoch and host observability, method labels do not explain additional spatial structure.

**Analysis:** compare longitude, latitude, heliocentric distance, and Galactic height by method; report effect sizes and bootstrap intervals; use energy distance or another multivariate two-sample statistic; separate targeted and survey discoveries where metadata permits.

**Immediate deliverable:** a methods-by-distance panel, sky-density projection, and table of medians, quantiles, and Galactic-centre fractions.

### Study 2 - Discovery-front expansion

**Question:** How did the observable volume and method mix change from 1992 to 2026?

**Analysis:** animate the cumulative record; compute yearly median and 90th-percentile distance by method; annotate mission eras; report both planet and unique-host counts so multi-planet systems do not dominate.

**Caution:** discovery year is bibliographic history, not a uniformly sampled observing epoch.

### Study 3 - Selection-aware candidate stability

**Question:** Which high-ranked candidates remain high when uncertain or inferred quantities are perturbed?

**Analysis:** retain the existing Monte Carlo propagation, then add rank-stability summaries, leave-one-axis-out rankings, and coherent-source versus composite-source sensitivity. Report the probability of appearing in the top 5, 10, and 20 rather than presenting one exact rank as immutable.

### Study 4 - From catalogue density to occurrence, only where defensible

**Question:** Can any spatial occurrence comparison be estimated from this project?

**Requirement:** add a surveyed-star denominator and a detection/completeness model for one well-defined survey such as Kepler. Do not combine heterogeneous confirmed planets into a single Galactic occurrence estimator.

**Analysis:** begin with a deliberately narrow replication of a published Kepler selection-function result. Only after validation should the model be extended.

## Priority roadmap

### Completed in this upgrade

- discovery-year playback in the real 3D system map;
- explicit “archive history, not stellar motion” interpretation;
- accessible play/pause, range, and show-all controls;
- method and distance filtering retained during playback;
- genuine SVG camera framing in the Galaxy view;
- deterministic, collision-free shell labels;
- public wording changed from specialist “provenance” labels to “source trail,” “measurement sources,” and “mass evidence” while preserving the scientific data model;
- a new research-article subsection defining the selection-aware contribution and its limits.

### Next research release

1. Add a 2D Galactic longitude/latitude fallback and downloadable filtered table for accessibility and verification.
2. Add yearly method-share and distance-quantile plots linked to the 3D timeline.
3. Export Gaia parallax error, RUWE, and match-quality fields into the Universe dataset; encode positional confidence without suggesting a precise 3D uncertainty sphere when distance posteriors are asymmetric.
4. Add a linear/log radial-scale toggle with an explanatory scale legend.
5. Add unique-host and planet-count modes.
6. Pre-register Study 1’s hypotheses, exclusions, statistics, and plots before interpreting the result.
7. Publish a versioned archive snapshot or DOI-backed release before seeking formal scientific review.

## Sharing strategy

For Slack, astronomy forums, and research-software groups, ask for focused criticism:

- “Is the discovery-map interpretation scientifically clear?”
- “Which selection effects are still easy to misread?”
- “Are the ranking axes and evidence labels understandable?”
- “What would be required before you would treat Study 1 as publishable?”
- “Which visual needs a downloadable or 2D verification view?”

Avoid presenting the project as a discovery of an Earth twin. A suitable short description is:

> Finding Earth 2.0 is a reproducible, selection-aware exploration of confirmed exoplanets. It connects candidate ranking and measurement quality to a 3D history of how different detection methods built the observed catalogue. I am sharing it for critique of the scientific assumptions, selection-effect treatment, and visual interpretation.

## Sources

1. NASA Science, [Eyes on Exoplanets](https://science.nasa.gov/exoplanets/eyes-on-exoplanets-web/).
2. NASA Exoplanet Archive, [Planetary Systems table column definitions](https://exoplanetarchive.ipac.caltech.edu/docs/API_PS_columns.html).
3. NASA Exoplanet Archive, [Exoplanet criteria for inclusion](https://exoplanetarchive.ipac.caltech.edu/docs/exoplanet_criteria.html).
4. Maliuk, A. & Budaj, J. (2020), [Spatial distribution of exoplanet candidates based on Kepler and Gaia data](https://doi.org/10.1051/0004-6361/201936692), *Astronomy & Astrophysics*, 635, A191.
5. Foreman-Mackey, D., Hogg, D. W. & Morton, T. D. (2014), [Exoplanet population inference and the abundance of Earth analogs from noisy, incomplete catalogs](https://doi.org/10.1088/0004-637X/795/1/64), *The Astrophysical Journal*, 795, 64.
6. Reid, M. J. et al. (2019), [Trigonometric parallaxes of high-mass star-forming regions: our view of the Milky Way](https://arxiv.org/abs/1910.03357), *The Astrophysical Journal*.
7. Gaia Collaboration, [Gaia DR3 documentation: astrometric data and transformations](https://gea.esac.esa.int/archive/documentation/GDR3/index.html).
8. McDonald, I. et al. (2022), [The Gaia DR3 selection function](https://arxiv.org/abs/2208.09335).
9. Henderson, C. B. et al. (2016), [Campaign 9 of the K2 mission: observational parameters, scientific drivers, and community involvement for a simultaneous space- and ground-based microlensing survey](https://doi.org/10.1088/1538-3873/128/970/124401), *PASP*, 128, 124401.
10. W3C WAI, [Understanding WCAG 2.2.2: Pause, Stop, Hide](https://www.w3.org/WAI/WCAG21/Understanding/pause-stop-hide.html).
11. Three.js, [InstancedMesh documentation](https://threejs.org/docs/pages/InstancedMesh.html).

## Bottom line

There is a proper research project here, but its strongest question is not “can we make NASA’s planet list look more realistic?” It is “can we make the observational construction, uncertainty, and limits of that list visible enough to support reproducible questions?” The current upgrade establishes that direction. A publishable scientific result should come next from one narrow, pre-specified analysis with an explicit selection function—not from adding more visual spectacle.
