# HWO precursor atlas and direct-imaging physics

Status: **Phase 10 release**. This product integrates public precursor catalogues
and evaluates explicit imaging trade cases. It is not a final HWO target list,
mission yield, flight design, or exo-Earth detection.

## Public catalogues

The complete 12,944-row [HPIC v1.1](https://doi.org/10.5281/zenodo.17178761)
is the atlas backbone. It preserves the source identifiers, sky coordinates,
photometry, stellar properties, source flags, reference bibcodes, multiplicity
information, Gaia contaminant fields, and known-host flag published by Tuchow
et al. HPIC membership means that a star belongs to a broad preliminary input
catalogue; it does not mean HWO will observe it.

The [TSS25 list](https://doi.org/10.5281/zenodo.17195128) is joined by the exact
HPIC `star_name`. Its 164 tier-1, 495 tier-2, and 12,285 tier-3 memberships remain
a separate community precursor-priority classification. TSS25 does not replace
HPIC and its tier is not treated as a detection probability.

Both CC BY 4.0 archives are pinned by byte count, MD5 and SHA-256 in
`data/manifests/hwo_hpic.json`. Raw archives remain outside Git; the fetch script
downloads the exact Zenodo payloads, extracts only declared members, rejects
unsafe paths, and verifies the extracted science tables.

## Nearby-star atlas

The derived atlas adds Galactic longitude and latitude, linear stellar
luminosity, and an Earth-equivalent-insolation distance

\[
a_{\rm EEID}=\sqrt{L_\star/L_\odot}\;{\rm au},\qquad
\theta_{\rm EEID}=1000\,a_{\rm EEID}/d\;{\rm mas}.
\]

It also evaluates the conservative runaway-greenhouse and maximum-greenhouse
distances with the existing Kopparapu erratum implementation, only inside its
2,600–7,200 K validity interval. The catalogue supports an EEID angular scale
for 12,682 stars and conservative HZ geometry for 12,405; missing or out-of-domain
rows stay unavailable.

## Direct-imaging probability

Reflected light uses

\[
C(\alpha)=A_g\Phi_{\rm L}(\alpha)(R_p/r)^2,
\]

with the Lambert phase function. Kepler's equation supplies orbital radius;
inclination, eccentricity, argument of periapsis, and mean anomaly determine the
sky-projected separation and phase angle. The analytic inner working angle is
`N lambda / D`. A reusable interface also accepts tabulated contrast curves.

Three generic trade cases expose diameter and wavelength sensitivity: 6 m at
500 nm, 8 m at 500 nm, and 6 m at 750 nm, each with `N=3` and a constant
`1e-10` contrast floor. These values are SCENARIO assumptions, not a statement
about the final HWO architecture.

For each hypothetical Earth-equivalent-insolation planet, 512 deterministic
draws propagate HPIC distance and log-luminosity errors, isotropic orientation,
uniform orbital phase and periapsis, eccentricity from 0–0.2, radius from
0.8–1.2 Earth radii, and geometric albedo from 0.1–0.4. The resulting
`p_observable` is a catalogue-conditioned FORECAST for a planet whose existence
is not asserted. It is not an occurrence or yield estimate.

The known-planet calculation exactly matches 744 planets across 464 HPIC hosts;
694 have distance, semimajor axis, and radius support. Published inclination and
eccentricity values and asymmetric errors are propagated when available;
declared priors fill missing orbital dimensions. For 406 matched RV planets,
`M sin i` remains the recorded quantity and a separately named true-mass
scenario is computed from the sampled inclination. It is never silently
relabeled as measured true mass.

## Reproduction

```powershell
python.exe scripts/fetch_hwo_catalogs.py
python.exe scripts/build_hwo_atlas.py
python.exe -m pytest tests/test_hwo_imaging.py
python.exe scripts/check_release_invariants.py
```

The full derived atlas, exo-Earth hypotheses, known-planet forecasts, figure,
summary and product hashes are committed under `results/hwo/`.
