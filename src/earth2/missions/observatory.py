"""Mission-specific evidence contracts for the Finding Earth 2.0 observatory.

Each mission retains its own measurement space, maturity, and claim boundary.
The module deliberately exposes no cross-mission ranking or aggregate metric.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass

EVIDENCE_LABELS = frozenset(
    {"OBSERVED", "DERIVED", "MODEL-INFERRED", "SCENARIO", "FORECAST", "SIMULATED"}
)


class FutureReleaseUnavailableError(ValueError):
    """Raised when unreleased mission data are presented as observations."""


@dataclass(frozen=True)
class ReleaseAdapter:
    """Version gate for public mission data and future ingestion contracts."""

    mission_id: str
    public_releases: tuple[str, ...]
    future_releases: tuple[str, ...]

    def evidence_label(self, release_id: str) -> str:
        """Return OBSERVED only for a declared public release."""

        if release_id in self.public_releases:
            return "OBSERVED"
        if release_id in self.future_releases:
            raise FutureReleaseUnavailableError(
                f"{self.mission_id} release {release_id!r} is not public in this snapshot"
            )
        raise ValueError(f"unknown {self.mission_id} release {release_id!r}")


@dataclass(frozen=True)
class MissionProfile:
    """A mission view with an explicit measurement and inference boundary."""

    mission_id: str
    name: str
    agency: str
    status_as_of: str
    status: str
    scientific_role: str
    measures: tuple[str, ...]
    cannot_measure: tuple[str, ...]
    wavelength: tuple[str, ...]
    resolution: tuple[str, ...]
    data_available: tuple[str, ...]
    forecast_boundary: str
    official_source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        text_fields = (
            self.mission_id,
            self.name,
            self.agency,
            self.status_as_of,
            self.status,
            self.scientific_role,
            self.forecast_boundary,
        )
        if any(not value.strip() for value in text_fields):
            raise ValueError("mission profile text fields must be non-empty")
        groups = (
            self.measures,
            self.cannot_measure,
            self.wavelength,
            self.resolution,
            self.data_available,
            self.official_source_ids,
        )
        if any(not group or any(not value.strip() for value in group) for group in groups):
            raise ValueError("mission profile evidence groups must be non-empty")

    def to_dict(self) -> dict[str, object]:
        """Return a stable JSON-compatible record."""

        return asdict(self)


MISSION_PROFILES: tuple[MissionProfile, ...] = (
    MissionProfile(
        mission_id="jwst",
        name="James Webb Space Telescope",
        agency="NASA / ESA / CSA",
        status_as_of="2026-09-12",
        status="operational observatory; public atmospheric reductions available",
        scientific_role="Existing and planned infrared atmospheric characterisation",
        measures=(
            "wavelength-dependent transit and eclipse depths",
            "direct spectra and images of sufficiently bright, widely separated companions",
            "time-series spectrophotometry constrained by instrument modes and target brightness",
        ),
        cannot_measure=(
            "life or habitability from a spectrum alone",
            "a unique atmospheric composition without retrieval assumptions and degeneracy tests",
            "Earth-Sun analogues in reflected light at HWO-like angular separation and contrast",
        ),
        wavelength=(
            "JWST instruments collectively: approximately 0.6-28 micrometres",
            "NIRSpec: 0.6-5.3 micrometres",
            "NIRISS SOSS: 0.6-2.8 micrometres",
            "MIRI MRS: 4.9-27.9 micrometres at useful detector response",
        ),
        resolution=(
            "NIRSpec spectroscopy: resolving power about 100, 1,000, or 2,700",
            "NIRISS SOSS: resolving power about 700",
            "MIRI MRS: resolving power about 3,500 at 5 micrometres to 1,500 at 28 micrometres",
        ),
        data_available=(
            "NASA Exoplanet Archive published spectrum index and atmospheric tables",
            "separate literature reductions with bibcodes, facilities, instruments, and archive paths",
            "programme identifiers and complete planned/approved/scheduled status are unavailable in the pinned archive tables",
        ),
        forecast_boundary=(
            "The observatory records published reductions as observations. Scale-height signals and "
            "unexecuted programme states remain scenarios or forecasts."
        ),
        official_source_ids=("jwst_instruments", "jwst_nirspec", "jwst_niriss", "jwst_miri"),
    ),
    MissionProfile(
        mission_id="hwo",
        name="Habitable Worlds Observatory",
        agency="NASA",
        status_as_of="2026-09-12",
        status="pre-formulation concept and technology maturation",
        scientific_role="Future reflected-light detection and spectroscopy of terrestrial planets",
        measures=(
            "planned direct imaging of reflected ultraviolet, visible, and near-infrared light",
            "planned spectroscopy of planetary atmospheres separated from host-star light",
            "planned system-level context for nearby stars and planets",
        ),
        cannot_measure=(
            "anything observationally before an observatory is built and commissioned",
            "life from a single gas or spectrum without environmental and false-positive context",
            "a guaranteed exo-Earth yield from a preliminary input catalogue",
        ),
        wavelength=("ultraviolet / visible / near-infrared; final bandpasses remain under study",),
        resolution=(
            "final telescope aperture, coronagraph performance, inner working angle, and spectral resolution are not fixed",
        ),
        data_available=(
            "HPIC v1.1 precursor-star measurements",
            "TSS25 community priority tiers",
            "generic analytic accessibility scenarios from this project; no HWO observations",
        ),
        forecast_boundary=(
            "HPIC and TSS25 are source catalogues. All planet accessibility values in this project are "
            "forecasts under declared generic coronagraph assumptions, not a mission yield."
        ),
        official_source_ids=("hwo_overview",),
    ),
    MissionProfile(
        mission_id="andes",
        name="ELT / ANDES",
        agency="European Southern Observatory and ANDES consortium",
        status_as_of="2026-09-12",
        status="second-phase ELT instrument in development",
        scientific_role="Future high-resolution spectroscopy, precision radial velocity, and atmosphere pathways",
        measures=(
            "resolved high-dispersion spectral lines from 0.4-1.8 micrometres in the baseline design",
            "precision Doppler shifts and atmospheric molecular cross-correlation signals",
            "stellar composition, activity, and line-profile diagnostics",
        ),
        cannot_measure=(
            "ANDES observations before instrument commissioning",
            "surface habitability or biology directly",
            "all terrestrial atmospheres independent of host brightness, tellurics, geometry, and exposure time",
        ),
        wavelength=("0.40-1.80 micrometres baseline; 0.35-2.40 micrometres goal",),
        resolution=(
            "baseline resolving power about 100,000",
            "baseline wavelength precision 1 metre per second; goals are not achieved performance",
        ),
        data_available=(
            "official design requirements and exposure-time calculator",
            "no ANDES science observations in the current project snapshot",
        ),
        forecast_boundary=(
            "Instrument specifications describe a design. Target pathways remain forecasts until public "
            "ANDES observations and reductions exist."
        ),
        official_source_ids=("andes_design",),
    ),
    MissionProfile(
        mission_id="plato",
        name="PLATO",
        agency="European Space Agency",
        status_as_of="2026-09-12",
        status="spacecraft testing; launch planned for March 2027",
        scientific_role="Future bright-star terrestrial discovery and stellar characterisation",
        measures=(
            "visible-light transit photometry with 26 cameras",
            "planet radii and orbital periods from transit light curves",
            "host-star oscillations for stellar radii, masses, and ages where supported",
        ),
        cannot_measure=(
            "PLATO discoveries before public mission data releases",
            "planet mass from photometry alone in the general case",
            "atmospheric composition or confirmed habitability from transit discovery photometry",
        ),
        wavelength=("visible-light photometry; response varies with camera class",),
        resolution=("time-series photometric cadence and precision, not a spectroscopic resolving power",),
        data_available=(
            "official mission design and status",
            "future release adapter only; no PLATO observations in the current project snapshot",
        ),
        forecast_boundary=(
            "Expected target counts and science capabilities are forecasts. The adapter refuses to label "
            "pre-release PLATO rows as observations."
        ),
        official_source_ids=("plato_overview", "plato_factsheet"),
    ),
    MissionProfile(
        mission_id="gaia",
        name="Gaia",
        agency="European Space Agency / Gaia DPAC",
        status_as_of="2026-09-12",
        status="Gaia DR3 public; Gaia DR4 not public in this snapshot",
        scientific_role="Astrometry, distances, stellar context, multiplicity, and future orbital solutions",
        measures=(
            "positions, parallaxes, proper motions, photometry, and selected radial velocities",
            "astrometric quality and non-single-star indicators",
            "release-specific astrophysical and variability products",
        ),
        cannot_measure=(
            "unreleased Gaia DR4 quantities",
            "planet atmosphere composition",
            "habitability from astrometry or multiplicity alone",
        ),
        wavelength=("broad optical G, BP, and RP photometry; RVS spectroscopy for supported sources",),
        resolution=("mission scanning astrometry and release-specific spectrophotometric/RVS products",),
        data_available=(
            "exact-source Gaia DR3 crossmatch for confirmed-planet hosts",
            "versioned DR4 schema contract with ingestion disabled until public release",
        ),
        forecast_boundary=(
            "Only DR3 rows are observations here. DR4 expectations describe a future release and cannot "
            "populate observed fields until an official public archive release is verified."
        ),
        official_source_ids=("gaia_dr3", "gaia_dr4"),
    ),
    MissionProfile(
        mission_id="roman",
        name="Nancy Grace Roman Space Telescope",
        agency="NASA",
        status_as_of="2026-09-12",
        status="launched 2026-08-30; travelling to Sun-Earth L2 and not yet in science operations",
        scientific_role="Future microlensing demographics across cold, wide-orbit, and free-floating planets",
        measures=(
            "planned high-cadence wide-field infrared microlensing light curves",
            "planned demographic sensitivity complementary to transit surveys",
            "planned multiband stellar photometry and grism context in Galactic-bulge fields",
        ),
        cannot_measure=(
            "Roman survey planets before science operations and public releases",
            "atmospheric composition for the statistical microlensing sample",
            "habitability from a lensing light curve",
        ),
        wavelength=("WFI infrared filters; GBTDS high cadence uses the broad F146 filter",),
        resolution=(
            "GBTDS recommended high-cadence observations every 12.1 minutes over six seasons",
        ),
        data_available=(
            "verified launch status and current survey design",
            "historical NASA Archive microlensing catalogue for context, explicitly not Roman observations",
            "future Roman release adapter; no Roman science rows in the current project snapshot",
        ),
        forecast_boundary=(
            "Roman is in post-launch transfer to L2. Survey yields and cadence are forecasts/design; "
            "the historical microlensing comparison table is not attributed to Roman."
        ),
        official_source_ids=("roman_launch", "roman_gbtds"),
    ),
)


RELEASE_ADAPTERS: tuple[ReleaseAdapter, ...] = (
    ReleaseAdapter("jwst", ("nea_atmosphere_2026-08-28",), ("future_archive_refresh",)),
    ReleaseAdapter("hwo", ("hpic_v1.1", "tss25_2025"), ("hwo_science_release",)),
    ReleaseAdapter("andes", (), ("andes_science_release",)),
    ReleaseAdapter("plato", (), ("plato_science_release",)),
    ReleaseAdapter("gaia", ("dr3",), ("dr4",)),
    ReleaseAdapter("roman", (), ("roman_science_release",)),
)


def validate_registry(profiles: Iterable[MissionProfile] = MISSION_PROFILES) -> None:
    """Validate completeness and scientific separation of the mission registry."""

    materialized = tuple(profiles)
    identifiers = [profile.mission_id for profile in materialized]
    if identifiers != ["jwst", "hwo", "andes", "plato", "gaia", "roman"]:
        raise ValueError("mission registry must contain the six ordered, separate mission views")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("mission identifiers must be unique")


validate_registry()


__all__ = [
    "EVIDENCE_LABELS",
    "MISSION_PROFILES",
    "RELEASE_ADAPTERS",
    "FutureReleaseUnavailableError",
    "MissionProfile",
    "ReleaseAdapter",
    "validate_registry",
]
