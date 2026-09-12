# Exoearth Evidence Observatory

Status: **Phase 14 website release**.

The website is the public reading layer for the generated results, not a second
scientific implementation. `scripts/build_web_observatory.py` reads the
authoritative files under `results/`, selects only the fields needed by the
browser, preserves claim boundaries and evidence labels, records every input
SHA-256, and writes `web/public/data/observatory.json` plus a compact
`release.json` freshness record.

## Narrative structure

The site now tells the research story in this order:

1. **Population** — what Kepler observed versus the population implied after
   selection correction.
2. **Selection** — transit geometry, observing window, injection-calibrated
   recovery and vetting over the declared DR25 domain.
3. **Climate** — time-dependent stellar luminosity and sensitivity to named
   habitable-zone prescriptions.
4. **Stellar environment** — present SED-derived UV/XUV evidence separated from
   evolutionary and atmospheric-escape scenarios.
5. **Atmospheres** — published measurements and reductions separated from
   scale-height scenarios.
6. **HWO** — precursor catalogues separated from analytic imaging forecasts.
7. **Missions** — JWST, HWO, ANDES, PLATO, Gaia and Roman retain independent
   scientific roles and release states.
8. **Information gain** — target/action posterior shrinkage under declared
   synthetic likelihoods.
9. **Model sensitivity** — rank and physical-model ranges remain visible.
10. **Falsification** — Solar-System controls expose where similarity and HZ
    metrics fail.
11. **Evidence graph** — example quantities can be traced back through the
    measurement and source graph.

The `/perspective` chapter is explicitly authored by Biswajit Jana. It contains
the learning log, a research dictionary and an author conclusion. It does not
present personal interpretation as an agency or community consensus.

## Automatic updates

GitHub Actions runs the archive and v2 rebuild once per day even when the
author's computer is off. A refresh opens a pull request only after the analysis
and tests complete. The deployed browser checks the small committed
`release.json` from GitHub `main` whenever the site opens. It can therefore say
whether the bundled page matches the latest reviewed research snapshot without
downloading raw archives or running scientific models on a reader's device.

## Interaction and motion

- The 3-D sky and Galaxy views render catalogue coordinates; they are not a
  decorative particle field.
- Motion uses opacity and transforms for entry or state continuity. Operating
  system reduced-motion preferences disable or shorten it.
- Every interactive control is keyboard operable and has a visible text or
  accessible name.
- Evidence state is written as text and never communicated by colour alone.
- The Universe overlay reserves separate layout rows for upper controls and the
  discovery-history console. The regression audit measures zero overlap at
  1365×773 and 390×844 viewports.

The visual direction draws on interaction principles documented by
[Motion](https://motion.dev/), [Framer](https://www.framer.com/dictionary/framer-motion),
[21st.dev](https://21st.dev/) and the
[UI/UX Pro Max skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill).
No component source or branded visual asset was copied from those sites.

## Rebuild and validate

```bash
python scripts/build_web_observatory.py
pytest tests/test_web_observatory.py -q
cd web
npm run typecheck
npm run lint
npm run build
npm run check:export
# with `npm run dev` running in another terminal:
npm run audit:visual
```

