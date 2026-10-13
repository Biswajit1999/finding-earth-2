# Discovery Universe — planet and host counts (September 2026 snapshot)

This note reconciles the labels used by Finding Earth 2.0's **Discovery Universe**
and **Galactic overview**. It documents a fixed archive snapshot; these are
not live counts and should not be repeated as current NASA totals.

| Quantity | Count | Population |
| --- | ---: | --- |
| Confirmed exoplanets in the project's scientific summary | 6,366 | All confirmed planets in this release |
| Unique host systems in the project's scientific summary | 4,775 | All hosts, including entries without plotted distance |
| Plotted planet records | 6,338 | Planets passing the measured-position/distance row filter |
| Unique host names among the plotted planet records | 4,747 | Stars represented by the plotted records |
| Planet records excluded for missing distance | 28 | Confirmed planets with no usable position in this export |

**The accounting identity is 6,338 + 28 = 6,366.** The plotted objects
are *planet records*, not 6,338 unique stars or 6,338 independently
measured planet positions. All planets sharing one host use the same measured
host-star coordinates (RA, Dec, distance). Thus several points can overlap.

The interface's **Planets** mode counts individual planet records.
**Unique hosts** displays one point for each distinct host in the current
filtered selection, so it is a subset of (at most) the 4,747 plotted hosts.
For the "of N" display the denominator must depend on the selected mode
(6,338 for planets, 4,747 for unique hosts on the full snapshot).

The discovery-method counts refer to **all plotted planet records before
interactive filters**, not the current host-count selection. In particular,
4,693 of the plotted planet records have the discovery method Transit,
and 1,198 have Radial Velocity. Multiple planets around one host can be
counted separately. The apparent spatial distribution is shaped by
survey target selection and instrument sensitivity, not the Galaxy's true
underlying planet density.

Gaia DR3 is used for cross-matches/quality annotations where available;
the map itself uses the versioned host-star coordinates. The discovery-year
slider changes the *catalogue chronology*; it does not evolve stellar
coordinates or predict future transits.

## Why this distinction matters for the moving-observer research query

A future kinematic study must first collapse the planet records to distinct
host-star trajectories and then join planetary orbital parameters back to
each host. Propagating 6,338 independent "stars" would duplicate the
motion of multi-planet hosts and bias reported sky-motion distributions.
Orbital inclination and unknown node angles must be handled separately
from host-star proper motion. A Gaia quality filter and missing radial
velocity audit will be needed before making time-dependent forecasts.

**Sources:** `results/analysis_summary.json`, `web/public/data/universe.json`,
`web/public/data/galaxy.json`, `web/public/data/discovery_timeline.json`.
All are the project's September 2026 versioned release products.
