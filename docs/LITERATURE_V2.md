# Finding Earth 2.0 v2 literature and implementation audit

Research date: 2026-09-09. Primary-source methods and archive documentation
were checked before introducing the selection-function model. This is a living
audit: the first implementation-ready portion is DR25 selection and the
Poisson-process foundation. Later work packages below have source and domain
reviews; their numerical coefficients, full-text equations and release products
must be rechecked at implementation time. The final literature release gate
remains open until those checks and the published-result comparison are done.

No novelty claim follows from this review. Published occurrence inference,
evidence catalogues, stellar-environment studies and mission planning already
address substantial portions of the proposed programme. The project's testable
contribution must come from reproducible integration and validated experiments.

## Selection and occurrence: implementation decisions

### S1. Geometric selection

**Citation/identifier:** Kipping (2014), MNRAS 444, 2263,
[arXiv:1408.1393](https://arxiv.org/html/1408.1393v1),
[doi:10.1093/mnras/stu1561](https://doi.org/10.1093/mnras/stu1561).
**Physical problem/equation:** Eqs. 1–2 derive impact parameter and transit
probability from isotropic inclination, using the planet's argument of periapsis:
`p = (Rstar/a)(1+e sin(omega))/(1-e²)` for centre-crossing `b<1`.
**Domain/assumptions/data:** bound, non-colliding orbits, inferior-conjunction
approximation; theoretical geometry, not an empirical survey calibration.
**Project relationship/decision:** implement a named impact-parameter convention;
use `Rstar+Rp` for any overlap only when requested. DR25 injected `b` is uniform
from 0 to 1, so use centre-crossing geometry for that experiment.
**Limitations:** observed transiting eccentricities have a selection prior;
the small-star/conjunction approximation is inappropriate for grazing stellar
encounters. Never use stellar RV omega without converting its convention.

### S2. Pixel-level injection experiment

**Citation/identifier:** Christiansen (2017),
[KSCI-19110-001](https://exoplanetarchive.ipac.caltech.edu/docs/KSCI-19110-001.pdf),
especially §§2–4 and 7. **Problem/equations:** estimate conditional pipeline
recovery from injected versus recovered events; a binomial experiment, not an
observed planet population. **Data/domain:** official DR25 INJ1 on-target
experiment, with circular orbits and uniform `b` in [0,1]; stellar-dependent
radius/MES sampling and restricted M-dwarf periods.
**Assumptions/relationship:** match the selected stars and injection protocol.
**Decision:** ingest original injection identifiers, injected parameters,
expected MES and recovery flags. Preserve unsearched and missing cases.
**Limitations:** pooled radius-period bins inherit the experimental sampling
distribution; they are not automatically average completeness for every target.
The input radius and supplemental recovered-radius conventions differ.

### S3. Official DR25 product roles

**Citation/identifier:** NASA Exoplanet Archive,
[completeness products](https://exoplanetarchive.ipac.caltech.edu/docs/Kepler_completeness_reliability.html),
[simulated products](https://exoplanetarchive.ipac.caltech.edu/docs/KeplerSimulated.html),
[stellar documentation](https://exoplanetarchive.ipac.caltech.edu/docs/Kepler_stellar_docs.html).
**Problem/equations:** distinguish window, pipeline recovery, vetting and
false-alarm rejection; no universal completeness product.
**Data/domain:** DR25 stars, INJ1/2/3, inverted and scrambled TCEs.
**Assumptions:** only searched stars contribute exposure; missing completeness
columns can identify exclusions. The supplemental stellar delivery corrects
parameters for 779 stars.
**Decision:** version all products, join exact KIC/TCE identifiers, keep each
experiment separate. Fetch compact result tables before bulk light curves.
**Limitations:** an on-target recovery experiment cannot supply false-positive
rates by itself. KOI disposition score is not a calibrated reliability.

### S4. Per-target efficiency, window and noise

**Citation/identifier:** Burke & Catanzarite (2017),
[KSCI-19111-002](https://exoplanetarchive.ipac.caltech.edu/docs/KSCI-19111-002.pdf),
and [NASA KeplerPORTs](https://github.com/nasa/KeplerPORTs).
**Problem/equations:** a target's detection contour combines noise-dependent
MES, a measured detection-efficiency function and a phase-window function.
**Data/domain:** DR25 flux-level injection calibration, stellar CDPP slopes,
limb darkening, radius, duty cycle and data span; optional numerical FITS
window and one-sigma-depth products.
**Assumptions/decision:** apply the SOC 9.3 calibration only to its matched
sample; preserve separate conditional factors and their calibration status.
**Relationship:** provides the denominator missing from v1.
**Limitations:** a convenient analytic CDPP approximation is a scenario until
compared with these calibrated contours. Do not double-count the observing
window if recovery was estimated over all injected phases.

### S5. Poisson-process population likelihood

**Citation/identifier:** Foreman-Mackey, Hogg & Morton (2014), ApJ 795, 64,
[arXiv:1406.3020](https://arxiv.org/html/1406.3020v2),
[doi:10.1088/0004-637X/795/1/64](https://doi.org/10.1088/0004-637X/795/1/64).
**Problem/equations:** Eqs. 2–4 and Appendix A give
`log L = -integral(lambda_observed) + sum(log(lambda_observed(x_i)))`;
`lambda_observed=C lambda`. **Domain/data:** noisy censored exoplanet catalogues;
the paper's application used a different Kepler pipeline/sample from DR25.
**Assumptions/decision:** start with a piecewise-constant density in natural-log
period/radius and explicit summed stellar exposure. Derive the Gamma posterior
for integer Poisson cell counts and a declared Gamma prior as a simple limiting
case. **Relationship:** the statistical foundation, not a reproduction claim.
**Limitations:** bin migration and false positives require extensions; the
paper's simplifying no-false-positive assumption is not adopted for real DR25
Earth-domain inference. Host multiplicity challenges independent-event models.

### S6. Terrestrial occurrence and validation

**Citation/identifier:** Burke et al. (2015), ApJ 809, 8,
[arXiv:1506.04175](https://arxiv.org/abs/1506.04175).
**Problem/equations:** likelihood inference of terrestrial occurrence with
survey sensitivity. **Domain/data:** the Kepler GK sample and catalogue
version analysed by that study, not arbitrary confirmed planets.
**Assumptions:** parameterised radius/period distribution and documented
selection. **Decision/relationship:** use as a method/systematics benchmark;
do not import its efficiency coefficients into DR25 without validation.
**Limitations:** reliability, radii, completeness and stellar parameters all
contribute systematic uncertainty; matching only a headline number is inadequate.

### S7. Hierarchical/ABC FGK occurrence

**Citation/identifier:** Hsu et al. (2019),
[arXiv:1902.01417](https://arxiv.org/abs/1902.01417).
**Problem/equations:** forward population simulation and approximate Bayesian
computation in radius-period bins. **Data/domain:** Kepler DR25 with Gaia DR2
stellar radii; published benchmark includes 0.75–1.5 Earth radii and 237–500 d.
**Assumptions/decision:** compare only with the same radius, period, stellar
sample and uncertainty convention. **Relationship:** independent statistical
benchmark for the first occurrence experiment.
**Limitations:** the reported differential density Gamma_Earth is not an
integrated HZ occurrence; prior and boundary effects remain important.

### S8. HZ occurrence in incident flux

**Citation/identifier:** Bryson et al. (2021), AJ 161, 36,
[arXiv:2010.14812](https://arxiv.org/html/2010.14812v2).
**Problem/equations:** stellar-temperature-dependent occurrence in radius and
incident flux with completeness and reliability correction.
**Data/domain:** 0.5–1.5 Earth radii, stars 4800–6300 K, named classical HZ.
**Assumptions/decision:** label domain, HZ model and long-period extrapolation
with every eta_Earth. The reported conservative-HZ medians span 0.37–0.60 planets
per star under different completeness extrapolations, with broad intervals.
**Relationship:** required real-data comparison after synthetic validation.
**Limitations:** different stellar populations or extrapolation rules do not
define the same estimand; this project's own eta_Earth is not yet measured.

### S9. Vetting and reliability

**Citation/identifier:** Thompson et al. (2018), ApJS 235, 38,
[primary paper](https://archive.stsci.edu/files/live/sites/mast/files/home/missions-and-data/kepler/_documents/Thompson_2018_ApJS_235_38%281%29.pdf),
and Bryson et al. (2021), §III.3 and Appendix D above.
**Problem/equations:** candidate contamination and missed real signals are
different conditional probabilities. **Data/domain:** DR25 observed,
injected, inverted and scrambled TCEs; astrophysical FPP separately.
**Assumptions/decision:** keep false-alarm and astrophysical reliability
explicit. Do not multiply purity into detection efficiency. Retain candidate
membership uncertainty; fractional weighted counts alone are not an exact
Poisson likelihood. **Relationship:** prevents spurious long-period occurrence.
**Limitations:** rogue TCEs and inconsistent vetter versions must be excluded or
modelled consistently. A score cut requires new completeness calibration.

### S10. M dwarfs and yield-standard occurrence

**Citation/identifiers:** Hsu et al. (2020),
[arXiv:2002.02573](https://arxiv.org/abs/2002.02573);
ExoPAG [SAG13 closeout](https://exoplanets.nasa.gov/system/internal_resources/details/original/680_SAG13_closeout_8.3.17.pdf)
and [2019 standards report](https://science.nasa.gov/wp-content/uploads/2023/04/Standards_Team_Final_Report_2019-Oct-17.pdf).
**Problem/equations:** stellar-population-dependent occurrence; parametric
yield priors are not new detections. **Data/domain:** M-star DR25/Gaia/2MASS
inference versus G-dwarf mission-design summaries.
**Assumptions/decision:** maintain separate stellar-population contracts and
forecast priors. **Relationship:** comparisons and future yield sensitivity.
**Limitations:** neither M-dwarf occurrence nor SAG13 coefficients are universal
FGK/HWO truths. Verify detailed coefficient tables before any yield integration.

## Composition and climate: reviewed scope, coefficient checks deferred

| Method and primary citation / identifier | Problem and equations | Domain, assumptions and data | Project decision and limitations |
|---|---|---|---|
| Rogers (2015), [1407.4457](https://arxiv.org/abs/1407.4457) | Hierarchical fraction dense enough for iron/silicate interiors | Kepler planets with RV constraints, mostly periods below about 50 d | Retain v1 logistic as heuristic; 1.6 radii is not a universal 50% composition probability or proof of rock |
| Wolfgang, Rogers & Ford (2016), [1504.07557](https://arxiv.org/abs/1504.07557) | Probabilistic power law M(R) with intrinsic mass scatter | RV-measured transiting sub-Neptunes, physical-density constraint | Named predictive mass model; propagate hyperparameter scatter; never relabel a prediction as dynamical mass |
| Chen & Kipping (2017), [1603.08614](https://arxiv.org/abs/1603.08614) | Segmented probabilistic mass-radius forecasting | 316 calibration objects across broad mass regimes | Compare forecasts, preserve model samples; Terran class is a model regime, not verified Earth-like composition |
| Otegi, Bouchy & Helled (2020), [1911.04745](https://arxiv.org/abs/1911.04745) | Separate rocky and volatile-rich empirical power laws | Transiting objects below 120 Earth masses; populations overlap | Composition-model sensitivity; the population split and measurement-selection effects are assumptions |
| Kopparapu et al. (2013), [1301.6674](https://arxiv.org/abs/1301.6674), erratum [10.1088/0004-637X/770/1/82](https://doi.org/10.1088/0004-637X/770/1/82) | S_eff polynomial; a_HZ=sqrt(L/S_eff) | 2600–7200 K, 1D climate, specified gases; corrected coefficient set | Preserve existing validated coefficients and explicit extrapolation; HZ location cannot establish habitability |
| Kopparapu et al. (2014), [1404.5292](https://arxiv.org/abs/1404.5292) | Mass-dependent classical boundaries | 0.1–5 Earth masses; specified background N2 pressure scaling | Named alternative to v1, with source-checked coefficients required; not a free model-independent correction |
| Yang, Cowan & Abbot (2013), [1307.0515](https://arxiv.org/abs/1307.0515) | 3D climate and cloud feedback | Tidally locked climate simulations and explicit surface/cloud assumptions | Compare only the supported scenario/domain; do not shift every HZ boundary by a universal factor |
| Choi et al. (2016), [1604.08592](https://arxiv.org/abs/1604.08592) | MIST stellar-evolution tracks | MESA models; age, mass, metallicity and rotation determine a track | Ingest versioned tracks and interpolate inside their domain; age posterior required before precise HZ duration |
| Bressan et al. (2012), [1208.4498](https://arxiv.org/abs/1208.4498) | PARSEC stellar evolution and isochrones | Explicit composition/opacity and evolutionary assumptions | Independent track comparison; do not combine metallicity conventions silently |

For continuous HZ, the proposed project statistic is
`tau_HZ = integral I(S_outer(t)<L(t)/a²<S_inner(t)) dt`; it is cumulative
residence, **not necessarily a single continuous interval**. Report both total
residence and longest uninterrupted interval. Define the integration start,
stellar-age normalisation and pre-main-sequence treatment. An absent age or
track gives undetermined, not a nominal Gyr estimate. This statistic is a
project definition, not a measured lifetime or a claim of continuous surface
habitability. A dedicated continuous-HZ literature comparison remains required.

## Stellar environment and atmosphere: reviewed scope

| Method and primary citation / identifier | Problem and equation/model | Domain, assumptions and data | Project decision and limitations |
|---|---|---|---|
| France et al. (2016), [1602.09142](https://arxiv.org/abs/1602.09142); [MAST MUSCLES](https://stdatu.stsci.edu/hlsp/muscles) | Panchromatic stellar SED; integrate named wavelength bands, F=L/(4 pi a²) | Observed UV/X-ray sections mixed with reconstructed EUV and photospheric models | Preserve observed/reconstructed segments, epochs and variability; no single stellar-habitability penalty |
| Wilson et al. (2021), [2102.11415](https://arxiv.org/abs/2102.11415); [2025 survey paper](https://ntrs.nasa.gov/api/citations/20250000597/downloads/Wilson_2025_ApJ_978_85.pdf) | Mega-MUSCLES stellar radiation environment | M-dwarf SEDs and model-filled spectral gaps | Use current HLSP versions; one epoch is not an observed lifetime XUV history |
| Bourrier et al. (2017), [primary A&A article](https://www.aanda.org/articles/aa/full_html/2017/03/aa30238-16/aa30238-16.html), with Erkaev et al. tidal prescription | Energy-limited mass loss with heating efficiency, XUV radius and tidal correction | TRAPPIST-1 high-energy constraints and assumed escape regime | Named scenarios with dimensional checks; no atmosphere-presence conclusion from one escape rate |
| Kubyshkina et al. (2018), [1810.06920](https://arxiv.org/abs/1810.06920) | Hydrodynamic-grid approximation to escape | Hydrogen-dominated models on stated mass/radius/temperature/host ranges | Compare only inside grid; do not apply to Earth-like high-molecular-weight atmospheres without justification |
| Kempton et al. (2018), [1805.03671](https://arxiv.org/abs/1805.03671) | Transmission and emission metrics | Bright transiting planets and stated atmospheric assumptions | Retain TSM diagnostic; calculate composition-specific scale-height scenarios separately; metrics are not detections |
| Schwieterman et al. (2018), [1705.05791](https://arxiv.org/abs/1705.05791) | Contextual interpretation of remote biosignatures | Atmospheric photochemistry, stellar environment, abiotic production | Show competing explanations; no probability of biology from the available training/control set |
| NASA [atmospheric spectroscopy documentation](https://exoplanetarchive.ipac.caltech.edu/docs/atmospheres/atmospheres_home.html), [column definitions](https://exoplanetarchive.ipac.caltech.edu/docs/atmospheres/atmospheres_columns.html) | File-level spectra, metadata, separate reductions | Unified architecture replaces retired aggregate tables | New adapter should retain spectrum IDs, units and reduction provenance; never average unrelated spectra |
| NASA [NExoList announcement](https://exoplanetarchive.ipac.caltech.edu/docs/exonews_archive.html) | JWST observation/proposal status | Versioned programme metadata rather than atmospheric conclusions | Verify public machine interface before ingestion; planned, observed and published are distinct states |

Before stellar-history calculations: expand the primary review of age/activity,
rotation, flare frequency and XUV saturation/decay laws. Before transmission
signals: check the hydrostatic scale-height and annulus approximation against a
primary derivation; the planned mu scenarios are assumptions, not measurements.

## Imaging, missions and experimental design

| Method and primary citation / identifier | Problem and equations | Domain, assumptions and data | Project decision and limitations |
|---|---|---|---|
| Tuchow et al. (2024), [2402.08038](https://arxiv.org/abs/2402.08038) | HPIC nearby-star input catalogue | Approximately 13,000 bright nearby stars, not the 164-star precursor shortlist | Ingest full version with all identifiers; HPIC membership is not a detected terrestrial planet |
| HWO TSS25 community list, [2509.20544](https://arxiv.org/abs/2509.20544) | Updated prioritised target list | Different selection purpose from broad HPIC | Preserve both memberships and source dates; do not silently substitute TSS25 for HPIC |
| Stark et al. (2014), [1409.5128](https://arxiv.org/abs/1409.5128) | Direct-imaging yield optimisation and single-visit completeness | Mission throughput, IWA, contrast, exposure, albedo, orbits and occurrence scenarios | Use orbit sampling and explicit instrument configurations; yield is FORECAST, not a planet census |
| Ertel et al. (2020), [2003.03499](https://arxiv.org/abs/2003.03499) | HOSTS exozodi inference | LBTI N-band nulling and a dust-distribution model | Preserve measurements/limits; population dust priors are not measured dust for every HWO target |
| ESO [ANDES](https://elt.eso.org/instrument/ANDES/) | High-resolution visible/NIR spectroscopy | Instrument programme and future capabilities | Separate RV and high-resolution atmospheric paths; generic resolution is insufficient to predict precision |
| ESA [PLATO mission](https://www.esa.int/Science_Exploration/Space_Science/Plato) | Transits plus stellar characterisation | Official mission status; future catalogue contract | Store planned status and source date; no invented PLATO discoveries |
| ESA [Gaia DR4 page](https://www.cosmos.esa.int/web/gaia/data-release-4) | Future astrometry and time-series release | Official page still describes forthcoming products | Continue DR3 data; prepare a versioned DR4 adapter without fabricating rows or public-release status |
| NASA [Roman survey technical page](https://science.nasa.gov/mission/roman-space-telescope/galactic-bulge-time-domain-survey-technical/); [STScI documentation](https://roman-docs.stsci.edu/roman-community-defined-surveys/galactic-bulge-time-domain-survey) | Microlensing/time-domain population demographics | Versioned bulge survey design; field specifications can change | Use official latest field/config and forecast labels; no reuse of Kepler transit completeness |
| Loredo (2004), [Bayesian Adaptive Exploration, author manuscript](https://hosting.astro.cornell.edu/~loredo/bayes/bae.pdf) | Bayesian decision theory for observation selection | Prior predictive observation and likelihood/noise models | Prototype expected KL information gain with validated synthetic models; observing cost is separate unless justified |
| Lindley (1956), [doi:10.1214/aoms/1177728069](https://doi.org/10.1214/aoms/1177728069) | Expected information supplied by an experiment; expected posterior-to-prior KL divergence | Requires a prior predictive distribution and an explicit likelihood for every action | Implement the exact scalar linear-Gaussian limiting case first; report nats and bits; withhold actions lacking a defensible likelihood |
| Batalha & Line (2017), [1612.02085](https://arxiv.org/abs/1612.02085) | Atmospheric information content and JWST mode selection | Forward models, Jacobians, wavelength-dependent noise, clouds and stated atmospheric domain | Do not infer atmospheric EIG from scale height alone; require target/instrument forward models and covariance before ranking spectral actions |

Imaging equations to implement after full model review: reflected-light contrast
`A_g Phi(alpha)(Rp/r)²`, phase-projected separation and configurable `N lambda/D`
IWA. A nominal angular HZ radius is not detection probability. Information gain
is an expectation over possible future data, not the shrinkage after one chosen
synthetic observation. All priors, likelihoods and units must be exposed.

## Validation and unresolved research gates

The first numerical experiment must recover known simulated distributions,
including near-zero selection and deliberately wrong completeness. Report
interval coverage with finite-trial binomial uncertainty. Validate the
likelihood against an independent analytic limiting case. Separate exact
integer-count inference from approximate candidate-reliability weighting.

Next primary-review tasks: Christiansen et al. (2020) updated DR25 completeness,
current eta_Earth methodological work, explicit reliability calibration from
inverted/scrambled experiments, updated stellar radii and their correlations,
continuous-HZ definitions, stellar-age/XUV evolution, measured/limit likelihoods,
and individual leading-candidate mass papers. Before any final scientific claim,
finish full-text/model-specific checks for every implemented later method and
perform the published-domain validation. Source discovery or an abstract read
alone is not certification of numerical coefficients.
