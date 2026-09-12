# How Finding Earth 2.0 can be wrong

A research system should try to fail on objects whose outcomes are already known.
Finding Earth 2.0 therefore keeps Earth, Venus, Mars, Mercury, and Jupiter outside
the numbered exoplanet ranking and runs them through every current model that has
the required inputs.

## The Venus failure

Venus receives an Earth Similarity Index of **0.874**, even though its observed
surface is a hostile runaway-greenhouse environment. The classical conservative
habitable-zone model correctly returns zero for Venus, but neither result measures
surface habitability. This is the clearest falsification of any interpretation
that turns geometric/physical similarity into an Earth-like-surface claim.

Earth is recovered at ESI 1 and conservative-HZ probability 1. Mars also lies in
the implemented conservative HZ while its surface is cold, arid, and low pressure.
That second control shows why an HZ is an irradiation boundary rather than a
climate classification. Mercury and Jupiter expose the intended rejection of hot
inner worlds and gas giants.

## Composition controls

The radius-only Rogers view assigns high rocky probability to Earth, Venus, Mars,
and Mercury. That is useful for bulk class and insufficient for surface outcome.
The two-dimensional Zeng envelope supports Earth but is outside its declared grid
for several smaller controls; unsupported is retained as missing rather than forced
into a verdict. The Otegi mixture supports Earth and Venus, again demonstrating
that a rocky planet need not be habitable.

## Candidate robustness

The release also recomputes catalogue ordering under five declared legacy-weight
menus: baseline, equal, similarity emphasis, HZ emphasis, and observational-
confidence emphasis. Rank spans are measured against the full rankable catalogue,
so large shifts are possible. This is a diagnostic of the legacy presentation,
not a new scientific ranking.

For the 25 leading candidates, the sensitivity table additionally exposes ranges
across three Kopparapu boundary prescriptions, supported rocky-composition models,
three generic HWO accessibility cases, and the fixed atmospheric molecular-weight
contrast where available. A missing range means the model cannot accept that row.

These ranges cover only the models implemented here. Stability within this menu
does not prove stability under all plausible climate, interior, stellar, or
instrument models.

## Reproduction

Run `python scripts/build_falsification_robustness.py`. Outputs and hashes are in
`results/falsification/`; every control and candidate row traces to a committed
upstream product.
