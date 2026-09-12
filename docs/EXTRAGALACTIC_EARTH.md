# Beyond Earth 2.0: the extragalactic Earth problem

> **RESEARCH FUTURES.** This chapter contains observed facts, physics-based
> calculations, mission concepts, and research hypotheses. It is separate from
> the project's candidate and population results. It does not report an
> extragalactic Earth detection.

## The question

Could an Earth-sized planet ever be detected and characterised outside the
Milky Way? The physics does not forbid planets in other galaxies. It makes the
methods successful around nearby stars collapse under distance, photon loss,
crowding, angular resolution, and confirmation time.

## A larger data universe is not automatically a better experiment

Gaia DR3 contains positions and mean G brightnesses for about 1.806 billion
sources, including full astrometric solutions for about 1.46 billion. This
project uses exact Gaia IDs for 4,408 host matches because those rows answer a
planet-radius and host-quality question. Ingesting the whole catalogue would not
create 1.8 billion exoplanet observations.

The scalable path is query federation and evidence partitioning:

1. keep immutable query/manifests beside small derived products;
2. push spatial, temporal, quality, and identity filters to TAP/cloud archives;
3. partition time series by stable source and observing programme;
4. use columnar storage and lazy scans for millions of measurements;
5. summarize billion-source archives into validated support surfaces;
6. keep raw pixels and spectra with providers unless a release permits reuse;
7. record whether every object is a source, measurement, candidate, or planet.

This architecture can progress from $10^5$ archive records to $10^9$ sources
and trillions of epochs without calling every row an exoplanet datum. The
selection rule remains: add a dataset when it changes a physical inference or a
decision about the next observation.

## Flux: the first wall

For isotropic luminosity $L$ at distance $d$,

\[
F_\star = \frac{L}{4\pi d^2}.
\]

For an ideal Earth twin at quadrature, this module uses the explicit reflected
light scenario

\[
\frac{F_p}{F_\star}=A_g\Phi(\alpha)\left(\frac{R_\oplus}{1\,{\rm AU}}\right)^2,
\quad A_g=0.3,\quad \Phi(90^\circ)=1/\pi,
\]

which gives a contrast near $1.7\times10^{-10}$. Contrast is approximately
distance-independent for an unresolved system, but both star and planet photon
rates fall as $d^{-2}$. A twin in M51 at 8.6 Mpc is about
$7.4\times10^{11}$ times fainter than the same target at 10 pc. Real exposures
also face local/exozodiacal background, stellar leakage, detector noise,
bandwidth, wavefront stability, and unresolved neighboring stars.

`results/futures/extragalactic_earth_feasibility.csv` evaluates solar/Earth
analogues at 1.301 pc, 10 pc, 1 kpc, 780 kpc, 8.6 Mpc, and 100 Mpc. Its photon
column is deliberately labelled an optimistic upper bound: it converts all
reflected bolometric power into 550 nm photons for a 6 m, 20%-throughput
collector. It is a bound, not an exposure-time forecast.

## Angular resolution: separation is not characterisation

An Earth-Sun separation projects to

\[
\theta_{\rm sep}=\frac{1\,{\rm AU}}{d},
\]

and an Earth diameter to $2R_\oplus/d$. The Rayleigh scale
$\theta=1.22\lambda/D$ gives two different demands:

- **separate planet from star:** resolve one AU;
- **resolve the planet:** resolve an Earth diameter.

At M51, one AU is roughly 0.116 microarcseconds. Ideal diffraction at 550 nm
alone requires a baseline of about 1,190 km to separate the orbit and roughly
14 million km to resolve an Earth diameter. These values omit contrast control,
collecting area, interferometric phase stability, foregrounds, and crowding, so
they are lower bounds on a much harder system.

## Why standard methods break

| Method | Nearby Milky Way | External galaxy limit |
|---|---|---|
| Transit | Individual star and repeated depth | Stars blend into pixels; Earth depth remains only ~84 ppm on one star |
| Radial velocity | Repeated stellar spectra | Individual solar-type spectra and cm/s motion are inaccessible |
| Direct imaging | Milliarcsecond separation and ~$10^{-10}$ contrast | sub-microarcsecond separation plus vanishing photons and crowding |
| Microlensing | One-off planet perturbations can reach distant Galactic fields | Pixel lensing can indicate a mass-ratio anomaly, but host/planet properties are degenerate |
| X-ray eclipse | Tiny X-ray-emitting region can be fully occulted | Rare geometry; interpretation and repetition are difficult |
| Strong lensing | Can magnify unresolved sources | Does not automatically isolate an Earth from its host or crowded field |

Transit depth $(R_p/R_\star)^2$ does not weaken with distance for an isolated
star, but photon noise rises and the star becomes unresolved from neighbors.
Distance therefore destroys practical sensitivity without changing the formal
fractional depth.

## M51-ULS-1b: a disciplined case study

Di Stefano et al. reported a complete, short X-ray eclipse of the bright source
M51-ULS-1 and proposed a roughly Saturn-size object as one interpretation. M51
is about 8.6 Mpc (28 million light-years) away. The source is a young X-ray
binary containing a compact object, not a Sun-Earth analogue. The long proposed
orbit may prevent a repeat transit for decades.

The correct label is **UNCONFIRMED EXTRAGALACTIC PLANET CANDIDATE**. A single
event cannot support “detected extragalactic planet,” and it says nothing about
an extragalactic Earth.

## Could future concepts change the answer?

Kilometre-to-million-kilometre optical interferometers would need collecting
area, formation control, delay stability, and contrast performance far beyond a
simple diffraction baseline. Gravitational lenses can amplify remote sources,
but they introduce alignment, degeneracy, and reconstruction problems.

The Solar Gravitational Lens is a NASA NIAC research concept for nearby
exoplanets. Its focal region begins beyond roughly 550 AU and is not a shortcut
to resolving arbitrary planets in external galaxies. It exchanges telescope
aperture for a difficult decades-scale journey, precise alignment, solar-corona
subtraction, and scanning reconstruction.

For an Earth-Sun analogue at Local Group and M51 distances, direct detection and
atmospheric characterisation are not feasible with foreseeable observatories.
Extragalactic planet candidates may remain accessible through rare magnified or
compact-source events, but Earth-like size, orbit, atmosphere, and surface
conditions will generally not all be measurable. This negative feasibility
result is the present scientific conclusion.

## Distance, communication, and travel

The `/beyond` calculator reports parsecs, light-years, kilometres, minimum
one-way signal delay, and minimum round trip. For spacecraft speed $v=\beta c$,

\[
t_{\rm Earth}=d/v,\qquad
\gamma=\frac{1}{\sqrt{1-\beta^2}},\qquad
\tau_{\rm traveller}=t_{\rm Earth}/\gamma.
\]

A massive spacecraft cannot reach $c$. The light-speed row is a causal limit for
information. Acceleration, deceleration, shielding, energy, navigation, and
collisions make every constant-speed travel value optimistic.

## Technosignatures and the contact problem

The separate evidence framework includes narrow-band and broadband radio,
optical/near-IR pulses, industrial atmospheric species, artificial illumination,
waste heat, and anomalous transit structures. Each hypothesis needs repeatability,
localisation, instrument checks, natural alternatives, and independent follow-up.
An unexplained signal is not automatically intelligence. A non-detection limits
only the searched signal class, sensitivity, frequency or wavelength, time, and
sky coverage.

Communication adds a non-negotiable time axis. At distance $d$ light-years, the
earliest arrival is $d$ years and the earliest immediate reply is $2d$ years.
For M51, one message is already a 28-million-year archaeological observation of
the past.

## Evidence classes

- **OBSERVED FACT:** an archive measurement or documented event.
- **PHYSICS-BASED CALCULATION:** equations evaluated under stated inputs.
- **MISSION FORECAST:** performance conditional on an instrument concept.
- **RESEARCH HYPOTHESIS:** a testable but unconfirmed interpretation.
- **AUTHOR PERSPECTIVE / SPECULATION:** a clearly attributed question or view.

## Primary sources

- Di Stefano et al. (2021), M51-ULS-1b candidate,
  <https://doi.org/10.1038/s41550-021-01495-w>.
- ESA Gaia DR3 contents, <https://www.cosmos.esa.int/web/gaia/dr3>.
- NASA Technosignatures Workshop report, <https://arxiv.org/abs/1812.08681>.
- NASA NIAC Solar Gravitational Lens concept,
  <https://www.nasa.gov/general/direct-multipixel-imaging-and-spectroscopy-of-an-exoplanet-with-a-solar-gravitational-lens-mission/>.

## Long-term question

The task is to find a world, determine what it is, test whether its environment
could support life, search for biosignatures and technosignatures, calculate the
signal delay and physical travel limit, and identify the observation or
technology required next. The project must keep visible what we know, what we
infer, what we could test, and what we can only imagine.
