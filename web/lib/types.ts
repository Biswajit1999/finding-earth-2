/**
 * Types mirroring the Python pipeline's export contract.
 *
 * These describe what `python -m earth2 export` writes. They are deliberately
 * permissive about nulls: a missing measurement is the normal case in this
 * dataset, and any type that pretends otherwise would push the problem into
 * render code as a crash instead of into the UI as an honest "—".
 */

/** A value that may legitimately be unmeasured. */
export type Maybe = number | null;

export interface CatalogueColumns {
  pl_name: string[];
  hostname: string[];
  earth2_index: Maybe[];
  earth2_rank: Maybe[];
  score_earth_similarity: Maybe[];
  score_conservative_habitability: Maybe[];
  score_observational_confidence: Maybe[];
  score_characterisation_potential: Maybe[];
  esi_global_p50: Maybe[];
  esi_global_p16: Maybe[];
  esi_global_p84: Maybe[];
  hz_conservative_prob: Maybe[];
  hz_optimistic_prob: Maybe[];
  hz_conservative: Maybe[];
  hz_optimistic: Maybe[];
  hz_model_extrapolated: boolean[];
  rocky_plausibility: Maybe[];
  pl_rade: Maybe[];
  pl_rade_p16: Maybe[];
  pl_rade_p84: Maybe[];
  pl_bmasse: Maybe[];
  mass_class: (string | null)[];
  pl_dens_used: Maybe[];
  pl_orbper: Maybe[];
  pl_orbsmax: Maybe[];
  pl_orbeccen: Maybe[];
  insol_used: Maybe[];
  teq_used: Maybe[];
  st_teff: Maybe[];
  st_rad: Maybe[];
  st_mass: Maybe[];
  st_lum: Maybe[];
  st_spectype: (string | null)[];
  sy_dist: Maybe[];
  ra: Maybe[];
  dec: Maybe[];
  sy_vmag: Maybe[];
  sy_jmag: Maybe[];
  sy_kmag: Maybe[];
  discoverymethod: (string | null)[];
  disc_year: Maybe[];
  disc_facility: (string | null)[];
  tran_flag: Maybe[];
  rv_flag: Maybe[];
  n_references: Maybe[];
  composite_parameter_source_count?: Maybe[];
  composite_uses_mixed_sources?: boolean[];
  default_solution_parameter_coverage?: Maybe[];
  composite_default_median_fractional_difference?: Maybe[];
  mc_uncertainty_coverage: Maybe[];
  n_transmission_points: Maybe[];
  n_emission_points: Maybe[];
  tsm: Maybe[];
  rv_semi_amplitude_ms: Maybe[];
  ephemeris_uncertainty_2030_minutes?: Maybe[];
  max_angular_separation_mas?: Maybe[];
  reflected_light_contrast_ag0p3?: Maybe[];
  is_control: boolean[];
  rankable: boolean[];
}

export interface CatalogueFile {
  generated_utc: string;
  earth2_version: string;
  n_rows: number;
  format: "columnar";
  note: string;
  fields: string[];
  columns: CatalogueColumns;
}

/** One planet, materialised from the columnar arrays. */
export interface Planet {
  index: number;
  name: string;
  host: string;
  rank: Maybe;
  index_value: Maybe;
  similarity: Maybe;
  habitability: Maybe;
  confidence: Maybe;
  characterisation: Maybe;
  esi: Maybe;
  esiLo: Maybe;
  esiHi: Maybe;
  hzProb: Maybe;
  hzOptProb: Maybe;
  hzConservative: Maybe;
  hzExtrapolated: boolean;
  rocky: Maybe;
  rade: Maybe;
  radeLo: Maybe;
  radeHi: Maybe;
  mass: Maybe;
  massClass: string | null;
  density: Maybe;
  period: Maybe;
  smax: Maybe;
  ecc: Maybe;
  insol: Maybe;
  teq: Maybe;
  teff: Maybe;
  srad: Maybe;
  smass: Maybe;
  slum: Maybe;
  spectype: string | null;
  dist: Maybe;
  ra: Maybe;
  dec: Maybe;
  vmag: Maybe;
  jmag: Maybe;
  kmag: Maybe;
  method: string | null;
  discYear: Maybe;
  facility: string | null;
  transits: boolean;
  rv: boolean;
  nRefs: Maybe;
  compositeSourceCount: Maybe;
  compositeUsesMixedSources: boolean | null;
  defaultSolutionCoverage: Maybe;
  compositeDefaultDifference: Maybe;
  uncCoverage: Maybe;
  nTransmission: Maybe;
  nEmission: Maybe;
  tsm: Maybe;
  rvK: Maybe;
  ephemerisUncertainty2030Minutes: Maybe;
  maxAngularSeparationMas: Maybe;
  reflectedLightContrast: Maybe;
  isControl: boolean;
  rankable: boolean;
}

export interface UniverseFile {
  generated_utc: string;
  n_points: number;
  n_excluded_no_distance: number;
  subsampled: boolean;
  coordinate_system: string;
  note: string;
  x: number[];
  y: number[];
  z: number[];
  name: string[];
  host: string[];
  dist_pc: number[];
  earth2_index: Maybe[];
  esi: Maybe[];
  hz_prob: Maybe[];
  rade: Maybe[];
  teq: Maybe[];
  st_teff: Maybe[];
  method: (string | null)[];
  disc_year: Maybe[];
}

export interface SummaryFile {
  generated_utc: string;
  earth2_version: string;
  monte_carlo: {
    n_samples: number;
    seed: number;
    n_planets?: number;
    n_with_esi_posterior?: number;
    median_esi_width?: number;
    n_hz_conservative_prob_gt_0p5?: number;
    n_hz_conservative_prob_gt_0p9?: number;
    mean_uncertainty_coverage?: number;
  };
  scale: {
    total_source_records: number;
    n_datasets_retrieved: number;
    archives: string[];
  };
  population: {
    n_confirmed_planets: number;
    n_unique_host_systems: number;
    n_solar_system_controls: number;
    n_multi_planet_systems: number;
    discovery_methods: Record<string, number>;
    discovery_year_range: [number, number];
  };
  measurement_coverage: Record<string, number | Record<string, number>>;
  observational_products: Record<string, number>;
  gaia_crossmatch: {
    n_hosts_matched: number;
    n_ruwe_above_1p4: number;
    n_non_single_star_flagged: number;
    median_distance_disagreement_pct: number;
  };
  habitable_zone: Record<string, number | string>;
  atmosphere: Record<string, number | Record<string, number>>;
  candidates: Record<string, number | Record<string, number>>;
  ranking?: {
    n_rankable: number;
    n_not_rankable: number;
    weights: Record<string, number>;
    top_candidates: TopCandidate[];
  };
  measurement_provenance?: {
    n_links: number;
    by_kind: Record<string, number>;
    n_distinct_publications: number;
    n_with_ads_bibcode: number;
    most_cited_sources: Record<string, number>;
    archive_calculated_by_parameter: Record<string, number>;
  };
  provenance: {
    n_datasets: number;
    n_datasets_ok: number;
    total_source_records: number;
    archives: string[];
    datasets: DatasetManifestRow[];
  };
  software: Record<string, string>;
  runtime_seconds: number;
}

export interface TopCandidate {
  rank: number;
  pl_name: string;
  hostname: string;
  earth2_index: number;
  earth_similarity: number;
  conservative_habitability: number;
  observational_confidence: number;
  mass_class: string;
  pl_rade: number | null;
  sy_dist_pc: number | null;
}

export interface DatasetManifestRow {
  dataset_id: string;
  archive: string;
  source_table: string;
  n_rows: number;
  n_columns: number;
  retrieved_utc: string;
  status: string;
  sha256_short: string;
  doi: string;
}

export interface SpectrumPoint {
  wavelength_um: number;
  bandwidth_um: number | null;
  depth_ppm: number;
  depth_ppm_err: number | null;
  source: string;
  facility: string | null;
  instrument: string | null;
}

export interface ExpectedBand {
  species: string;
  label: string;
  bands_um: number[];
  colour_role: string;
  biosignature_relevance: string;
  status: string;
}

export interface TransmissionSpectrum {
  available?: false;
  message?: string;
  planet?: string;
  kind?: string;
  n_points?: number;
  wavelength_range_um?: [number, number];
  facilities?: string[];
  instruments?: string[];
  depth_sources?: Record<string, number>;
  expected_bands?: ExpectedBand[];
  points?: SpectrumPoint[];
  caveat?: string;
}

export interface DeepDive {
  planet: string;
  hostname: string;
  generated_utc: string;
  narrative: {
    location: string | null;
    host_star: string | null;
    system: string | null;
    planet: string | null;
    climate: string | null;
  };
  visualisation_disclaimer: string;
  ranking: {
    earth2_rank: number | null;
    earth2_index: Maybe;
    scores: Record<string, Maybe>;
    component_ranks: Record<string, number | null>;
  };
  planet_parameters: Record<string, any>;
  host_star: Record<string, any>;
  gaia_crossmatch: Record<string, any> | null;
  habitable_zone: Record<string, any>;
  earth_similarity: Record<string, any>;
  evidence: Record<string, any>;
  observability: Record<string, any>;
  system: { siblings: any[] };
  measurement_provenance?: ProvenanceRow[];
  identifiers?: Record<string, string | null>;
  aliases?: string[];
  transmission_spectrum: TransmissionSpectrum;
  transit_analysis: Record<string, any>;
  rv_analysis: Record<string, any>;
}

export interface ProvenanceRow {
  parameter: string | null;
  parameter_label: string | null;
  value: Maybe;
  source_kind: string | null;
  reference_label: string | null;
  reference_url: string | null;
  bibcode: string | null;
}

export interface DeepDiveIndexEntry {
  planet: string;
  slug: string;
  hostname: string;
  earth2_index: Maybe;
  earth2_rank: number | null;
  distance_pc: Maybe;
  has_transmission_spectrum: boolean;
  has_rv_analysis: boolean;
  transit_status: string | null;
}

export interface CoverageRow {
  quantity: string;
  column: string;
  n_with_value: number;
  pct_with_value: number;
  n_with_uncertainty: number;
  pct_with_uncertainty: number | null;
}

export interface ReferenceRow {
  reference_label: string;
  reference_url: string | null;
  bibcode: string | null;
  n_measurements: number;
}

export interface TransitValidationTarget {
  planet: string;
  host: string;
  why: string;
  status: string;
  tmag: Maybe;
  period_days: Maybe;
  published_depth_ppm: Maybe;
  fitted_depth_ppm: Maybe;
  ratio_fitted_to_published: Maybe;
  validated: boolean;
  depth_snr: Maybe;
  duration_hours_fitted: Maybe;
  radius_ratio_approx: Maybe;
  cadence_precision_ppm: Maybe;
  n_cadences: number | null;
  folded_binned: {
    phase_hours: number[];
    flux: number[];
    flux_err: number[];
    n_bins: number;
    n_raw_points: number;
  } | null;
}

export interface TransitValidationFile {
  generated_utc: string;
  purpose: string;
  n_targets: number;
  n_attempted: number;
  n_validated: number;
  median_ratio_fitted_to_published: Maybe;
  systematic_note: string;
  targets: TransitValidationTarget[];
}

export interface SpectraIndexRow {
  pl_name: string;
  kind: string;
  n_points: number;
  wl_min_um: number;
  wl_max_um: number;
  n_facilities: number;
  facilities: string;
}
