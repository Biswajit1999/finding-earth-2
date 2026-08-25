"""Biosignature context.

This module deliberately computes **no probability of life**, and the project
will not add one. There is no calibrated likelihood function for biology on
exoplanets: we have one inhabited world, no confirmed uninhabited control with a
comparable atmosphere, and no complete theory of abiotic false positives. A
number like "68% chance of life" would be a fabricated statistic wearing a
decimal point.

What this module provides instead is the interpretive scaffolding a reader needs
to evaluate any claimed atmospheric detection: what each species would mean,
what produces it without life, and what would have to be true for a biological
interpretation to survive scrutiny.

The evidence ladder
-------------------
These are distinct states and the project keeps them distinct everywhere:

=========================  ====================================================
State                      Meaning
=========================  ====================================================
``expected_band``          The species absorbs in this wavelength range. Says
                           nothing about whether it is there.
``candidate_feature``      A feature is present near the band but is not
                           established as that species.
``reported_evidence``      A peer-reviewed analysis reports evidence for the
                           species, at that paper's stated confidence.
``contested``              Published analyses disagree, or a reanalysis of the
                           same data did not reproduce the result.
``non_detection``          The species was searched for and not found.
``upper_limit``            Abundance constrained to below some value.
``ambiguous``              Detected, but the abundance is consistent with both
                           biological and abiotic explanations.
=========================  ====================================================

Note there is no ``detected_biosignature`` state. Detecting a gas and detecting
life are separated by the entire remaining content of this module.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "BIOSIGNATURE_CONTEXT",
    "EVIDENCE_STATES",
    "FALSE_POSITIVE_MECHANISMS",
    "INTERPRETATION_REQUIREMENTS",
    "biosignature_context_for",
]

EVIDENCE_STATES: dict[str, str] = {
    "expected_band": "The species absorbs here. No claim that it is present.",
    "candidate_feature": "A feature near the band, not established as this species.",
    "reported_evidence": "A peer-reviewed analysis reports evidence, at its stated confidence.",
    "contested": "Published analyses disagree or a reanalysis did not reproduce it.",
    "non_detection": "Searched for and not found.",
    "upper_limit": "Abundance constrained below a stated value.",
    "ambiguous": "Present, but consistent with biological and abiotic explanations alike.",
}

#: Known abiotic routes to gases often described as biosignatures.
#: Each is a documented mechanism from the atmospheric-photochemistry
#: literature, summarised for a general reader.
FALSE_POSITIVE_MECHANISMS: dict[str, list[dict[str, str]]] = {
    "O2": [
        {
            "mechanism": "Water photolysis with hydrogen escape",
            "description": (
                "Ultraviolet light splits water vapour; the light hydrogen escapes to space "
                "and leaves oxygen behind. A planet that lost an ocean this way can accumulate "
                "a thick abiotic O2 atmosphere."
            ),
            "where_it_matters": (
                "Planets around M dwarfs, which spend their first hundreds of millions of "
                "years far more luminous in the extreme ultraviolet than their main-sequence "
                "brightness suggests. A habitable-zone planet there can lose several oceans "
                "before the star settles."
            ),
        },
        {
            "mechanism": "CO2 photolysis in a dry atmosphere",
            "description": (
                "CO2 is broken into CO and O, which recombines into O2. Without water vapour "
                "to supply the catalytic hydrogen radicals that normally reverse this, oxygen "
                "builds up."
            ),
            "where_it_matters": "Dry, CO2-rich atmospheres around cool stars.",
        },
        {
            "mechanism": "Atmospheric escape from a low-gravity body",
            "description": (
                "Preferential loss of lighter species can enrich the remaining atmosphere in "
                "oxygen without any biological source."
            ),
            "where_it_matters": "Low-mass planets with weak gravitational binding.",
        },
    ],
    "O3": [
        {
            "mechanism": "Photochemical product of any O2",
            "description": (
                "Ozone forms from O2 by ultraviolet photochemistry, so it inherits every "
                "abiotic pathway O2 has. It is easier to detect at low abundance, which makes "
                "it a more sensitive proxy -- and an equally ambiguous one."
            ),
            "where_it_matters": "Anywhere O2 can be produced abiotically.",
        },
    ],
    "CH4": [
        {
            "mechanism": "Serpentinisation",
            "description": (
                "Water reacting with ultramafic rock releases hydrogen, which reduces carbon "
                "to methane. An entirely geological process."
            ),
            "where_it_matters": "Any world with water-rock interaction.",
        },
        {
            "mechanism": "Volcanic and magmatic outgassing",
            "description": "Methane is a normal component of volcanic outgassing.",
            "where_it_matters": "Geologically active worlds.",
        },
        {
            "mechanism": "Cometary delivery",
            "description": "Impacts deliver reduced carbon compounds.",
            "where_it_matters": "Young systems with high impact rates.",
        },
    ],
    "N2O": [
        {
            "mechanism": "Lightning and atmospheric chemistry",
            "description": "Non-biological nitrogen chemistry produces N2O at low levels.",
            "where_it_matters": "Nitrogen-rich atmospheres with electrical activity.",
        },
    ],
    "CH3Cl": [
        {
            "mechanism": "Volcanic halogen chemistry",
            "description": "Methyl chloride has volcanic as well as biological sources.",
            "where_it_matters": "Volcanically active worlds.",
        },
    ],
}

#: What would need to hold for a biological interpretation to be credible.
INTERPRETATION_REQUIREMENTS: list[dict[str, str]] = [
    {
        "requirement": "Chemical disequilibrium, not a single gas",
        "detail": (
            "Earth's most robust remote biosignature is not oxygen alone but oxygen "
            "coexisting with methane. The two react on timescales far shorter than a "
            "planet's lifetime, so finding them together implies something is continuously "
            "replenishing both. Any single gas has an abiotic story; a maintained "
            "disequilibrium is much harder to explain without a biosphere."
        ),
    },
    {
        "requirement": "The stellar environment must be characterised",
        "detail": (
            "Whether abiotic oxygen is expected depends on the host's ultraviolet history "
            "and current activity. Without that, an O2 detection cannot be interpreted at "
            "all -- the same measurement means different things around a quiet K dwarf and "
            "an active M dwarf."
        ),
    },
    {
        "requirement": "Clouds and hazes must be accounted for",
        "detail": (
            "High-altitude aerosols mute or flatten transmission features and mimic a "
            "high-mean-molecular-weight atmosphere. A flat spectrum is consistent with a "
            "cloudy hydrogen atmosphere AND with a compact heavy one; the two are not "
            "distinguishable without additional wavelength coverage."
        ),
    },
    {
        "requirement": "Retrieval degeneracies must be reported",
        "detail": (
            "Atmospheric retrievals trade abundance against reference pressure, temperature "
            "structure and cloud-top altitude. Different assumptions fit the same data with "
            "abundances differing by orders of magnitude. A quoted abundance without its "
            "degeneracies is not a measurement."
        ),
    },
    {
        "requirement": "The planet must be confirmed to have an atmosphere at all",
        "detail": (
            "For small planets around M dwarfs, the prior question is whether an atmosphere "
            "survived stellar activity. Several rocky planets observed with JWST are "
            "consistent with bare rock. Interpreting a marginal feature before establishing "
            "an atmosphere exists inverts the burden of proof."
        ),
    },
    {
        "requirement": "Independent reproduction",
        "detail": (
            "Marginal spectral features in exoplanet atmospheres have repeatedly failed to "
            "reproduce between instruments, pipelines and independent reanalyses of the same "
            "observations. A single analysis is a hypothesis."
        ),
    },
]

#: Per-species interpretive context.
BIOSIGNATURE_CONTEXT: dict[str, dict[str, Any]] = {
    "O2": {
        "why_discussed": "Earth's atmospheric oxygen is overwhelmingly biological in origin.",
        "why_not_conclusive": (
            "Several well-studied abiotic routes can produce comparable abundances, "
            "particularly around M dwarfs, which host most of the small planets we can "
            "currently characterise."
        ),
        "strengthened_by": ["Simultaneous CH4", "Absence of large CO abundance",
                            "Known quiet stellar UV history"],
        "weakened_by": ["Active M-dwarf host", "High CO abundance", "Evidence of past ocean loss"],
    },
    "O3": {
        "why_discussed": "A sensitive proxy for O2, detectable at lower abundances.",
        "why_not_conclusive": "Inherits every abiotic pathway available to O2.",
        "strengthened_by": ["Simultaneous CH4", "Constrained stellar UV"],
        "weakened_by": ["Any abiotic O2 source"],
    },
    "CH4": {
        "why_discussed": "Biologically produced on Earth and short-lived, so it must be replenished.",
        "why_not_conclusive": "Serpentinisation and volcanism produce it without biology.",
        "strengthened_by": ["Simultaneous O2 or O3", "Abundance exceeding plausible geological flux"],
        "weakened_by": ["Evidence of active volcanism", "Hydrogen-rich atmosphere"],
    },
    "H2O": {
        "why_discussed": "Necessary for life as we know it and a marker of volatile inventory.",
        "why_not_conclusive": "Ubiquitous, including in hot gas giants. Not a biosignature.",
        "strengthened_by": [],
        "weakened_by": [],
    },
    "CO2": {
        "why_discussed": "Establishes that an atmosphere exists and constrains its composition.",
        "why_not_conclusive": "Dominant on Venus and Mars, neither of which is inhabited at the surface.",
        "strengthened_by": [],
        "weakened_by": [],
    },
    "CO": {
        "why_discussed": "Diagnostic of photochemistry.",
        "why_not_conclusive": (
            "Usually an ANTI-biosignature: abundant CO alongside O2 points to CO2 photolysis "
            "rather than biology, and a biosphere would be expected to consume available CO."
        ),
        "strengthened_by": [],
        "weakened_by": [],
    },
    "SO2": {
        "why_discussed": "Its JWST detection demonstrated that photochemistry is observable in exoplanet atmospheres.",
        "why_not_conclusive": "Volcanic and photochemical. Not associated with biology.",
        "strengthened_by": [],
        "weakened_by": [],
    },
}


def biosignature_context_for(species: str) -> dict[str, Any]:
    """Everything the project is willing to say about one species.

    Returns interpretive context and known false positives. Never returns a
    probability, a score, or a verdict.
    """
    s = species.upper().replace("_", "")
    key = {"O2": "O2", "O3": "O3", "CH4": "CH4", "H2O": "H2O",
           "CO2": "CO2", "CO": "CO", "SO2": "SO2"}.get(s, s)

    return {
        "species": key,
        "context": BIOSIGNATURE_CONTEXT.get(key, {
            "why_discussed": "Not a species this project treats in a biosignature context.",
            "why_not_conclusive": "",
            "strengthened_by": [],
            "weakened_by": [],
        }),
        "abiotic_false_positives": FALSE_POSITIVE_MECHANISMS.get(key, []),
        "interpretation_requirements": INTERPRETATION_REQUIREMENTS,
        "project_position": (
            "This project reports where species absorb and what published analyses claim. "
            "It does not compute a probability of life, and does not treat any single gas "
            "as evidence of biology."
        ),
    }
