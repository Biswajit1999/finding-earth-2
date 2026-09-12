# Stellar UV/XUV environment

Status: **Phase 8 model release**. This layer keeps bolometric habitable-zone
position separate from high-energy irradiation. It does not compress XUV
exposure into a habitability score.

The release evaluates the 60 highest-ranked non-control planets at or below
2.5 Earth radii. Forty-six have the age, stellar mass and bolometric flux needed
for bounded history scenarios. Exact host matches use pinned MAST MUSCLES / Mega-MUSCLES
panchromatic SEDs for Proxima Centauri, GJ 667 C and TRAPPIST-1, covering nine
planet rows. The adapted
constant-resolution products are hash-verified and remain under the raw-data
policy. Their 5–912 Å XUV, 912–1700 Å FUV, 1700–3200 Å NUV and reconstructed
Ly-alpha bands are integrated with exact bin-edge overlap.

MUSCLES SEDs combine observed X-ray/UV spectra with reconstructed Ly-alpha,
empirically reconstructed or differential-emission-measure EUV, and modeled
spectral intervals. Their derived current fluxes are therefore labelled
**DERIVED FROM AN OBSERVED/RECONSTRUCTED/MODEL SED**, not simply observed.
Reported bin errors are propagated, but correlated stitching and model
systematics are not captured.

For the other targets, and for time integration, the code evaluates three
explicit saturated-then-decaying `L_XUV/L_bol` histories. The scenarios vary
saturation level, saturation lifetime and decay exponent, with longer
saturation windows for stars below 0.6 solar masses. They are bounded
hypotheses informed by the Ribas and Wright activity literature, not calibrated
posteriors for individual stars. A missing stellar age produces
`undetermined`, even when a current MUSCLES SED exists.

Primary archive and model references:

- MAST MUSCLES HLSP, doi:10.17909/T9DG6F.
- France et al. (2016), doi:10.3847/0004-637X/820/2/89.
- Youngblood et al. (2016), doi:10.3847/0004-637X/824/2/101.
- Wilson et al. (2025), doi:10.3847/1538-4357/ad9d95.
- Ribas et al. (2005), doi:10.1086/427977.
- Wright et al. (2011), doi:10.1088/0004-637X/743/1/48.

Reproduce with:

```powershell
python.exe scripts/fetch_muscles_xuv.py
python.exe scripts/build_xuv_escape.py
```
