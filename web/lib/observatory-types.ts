export type EvidenceLabel =
  | "OBSERVED"
  | "DERIVED"
  | "MODEL-INFERRED"
  | "SCENARIO"
  | "FORECAST"
  | "SIMULATED"
  | string;

export interface SelectionCell {
  period_days: number;
  planet_radius_earth: number;
  target_stars: number;
  mean_transit_geometry: number;
  mean_phase_window: number;
  mean_pipeline_including_window: number;
  mean_vetting_given_recovered: number;
  mean_pipeline_and_vetting: number;
  mean_total_selection: number;
  effective_stars: number;
  label: EvidenceLabel;
}

export interface InformationGainRow {
  label: EvidenceLabel;
  pl_name: string;
  earth2_rank: number;
  action_id: string;
  parameter: string;
  parameter_value: number | null;
  unit: string;
  prior_sigma: number | null;
  observation_sigma: number | null;
  expected_posterior_sigma: number | null;
  expected_information_gain_nats: number | null;
  expected_information_gain_bits: number | null;
  status: string;
  cost_or_time: string;
  within_target_information_rank: number | null;
}

export interface SensitivityRow {
  label: EvidenceLabel;
  pl_name: string;
  earth2_rank: number;
  legacy_rank_min: number;
  legacy_rank_max: number;
  legacy_rank_span: number;
  climate_status: string;
  hz_model_probability_min: number | null;
  hz_model_probability_max: number | null;
  hz_model_probability_range: number | null;
  p_rocky_model_min: number | null;
  p_rocky_model_max: number | null;
  p_rocky_model_range: number | null;
  hwo_accessibility_min: number | null;
  hwo_accessibility_max: number | null;
  hydrogen_to_earth_air_signal_ratio: number | null;
}

export interface MissionRecord {
  mission_id: string;
  name: string;
  scientific_role: string;
  status: string;
  status_as_of: string;
  labels_present: EvidenceLabel[];
  evidence_file: string;
  page: string;
}

export interface MissionDetail {
  mission: {
    mission_id: string;
    name: string;
    agency: string;
    status: string;
    scientific_role: string;
    measures: string[];
    cannot_measure: string[];
    data_available: string[];
    wavelength: string[];
    resolution: string[];
    forecast_boundary: string;
  };
  evidence_records: Array<{
    evidence_id: string;
    label: EvidenceLabel;
    value: number;
    unit: string;
    secondary_value?: number;
    secondary_unit?: string;
    interpretation: string;
  }>;
  official_sources: Array<{
    title: string;
    agency: string;
    url: string;
    supports: string;
  }>;
}

export interface ObservatoryData {
  schema_version: string;
  title: string;
  generated_utc: string;
  author: string;
  source_hashes: Record<string, string>;
  population: Record<string, unknown> & {
    title: string;
    label: EvidenceLabel;
    domain: Record<string, number>;
    funnel: Array<{ stage: string; value: number; unit: string; label: EvidenceLabel }>;
    intrinsic_posterior: Record<string, { p16: number; p50: number; p84: number }>;
    claim_boundary: string;
  };
  selection: {
    label: EvidenceLabel;
    scope: string;
    release_status: string;
    stellar_selection: Record<string, number>;
    stellar_denominator: Record<string, number>;
    calibration_sample: Record<string, number>;
    model: Record<string, unknown>;
    surface_grid: { period_points: number[]; radius_points: number[]; cells: number };
    cells: SelectionCell[];
    interpretation: string;
  };
  composition: Record<string, unknown> & {
    label: EvidenceLabel;
    population: Record<string, number | string | null>;
    model_disagreement: Record<string, unknown>;
    claim_boundary: string;
    records: Array<Record<string, unknown>>;
  };
  climate: Record<string, unknown> & {
    label: EvidenceLabel;
    population: {
      confirmed_planets_evaluated: number;
      inferred: number;
      classification_robustness: Record<string, number>;
      outcomes: Record<string, number>;
    };
    prescriptions: Record<string, unknown>;
    claim_boundary: string;
    records: Array<Record<string, unknown>>;
  };
  environment: Record<string, unknown> & {
    labels: EvidenceLabel[];
    population: Record<string, number>;
    claim_boundary: string;
    records: Array<Record<string, unknown>>;
  };
  atmosphere: Record<string, unknown> & {
    labels: EvidenceLabel[];
    spectrum_evidence: Record<string, number | string | unknown[]>;
    observability: Record<string, unknown>;
    records: Array<Record<string, unknown>>;
    earth_analogue_screen: Record<string, unknown> & {
      confirmed_planets: number;
      strict_small_temperate_candidates: number;
      strict_candidates_with_indexed_reductions: number;
      strict_candidates_with_tabulated_measurements: number;
      finding: string;
      next_observation: string;
      claim_boundary: string;
    };
  };
  hwo: Record<string, unknown> & {
    labels: EvidenceLabel[];
    catalogue: Record<string, number | string | Record<string, number>>;
    instrument_scenarios: Array<Record<string, number | string>>;
    exoearth_forecast: Record<string, unknown>;
    known_planet_forecast: Record<string, number>;
    claim_boundary: string;
    top_accessible_known_planets: Array<Record<string, number | string | null>>;
  };
  missions: {
    title: string;
    status_as_of: string;
    separation_policy: string;
    missions: MissionRecord[];
    details: Record<string, MissionDetail>;
  };
  information_gain: Record<string, unknown> & {
    title: string;
    label: EvidenceLabel;
    candidate_count: number;
    action_count: number;
    row_count: number;
    supported_rows: number;
    equation: string;
    linear_gaussian_solution_nats: string;
    claim_boundary: string;
    withheld_actions: Array<{ action_id: string; status: string; reason: string }>;
    rows: InformationGainRow[];
  };
  falsification: Record<string, unknown> & {
    labels: EvidenceLabel[];
    candidate_count: number;
    control_count: number;
    venus_esi: number;
    venus_conservative_hz_probability: number;
    venus_falsification: string;
    claim_boundary: string;
    controls: Array<Record<string, number | string | null>>;
    candidate_sensitivity: SensitivityRow[];
  };
  evidence: Record<string, unknown> & {
    edges: number;
    nodes_by_kind: Record<string, number>;
    quantity_labels: Record<string, number>;
    records_with_provenance_gaps: number;
    scope: string;
    mass_examples: Record<
      string,
      Array<{
        root: string;
        nodes: Array<{
          id?: string;
          kind?: string;
          label?: string | null;
          name?: string;
          attributes?: Record<string, unknown>;
        }>;
        edges: unknown[];
      }>
    >;
  };
}

export interface ObservatoryRelease {
  schema_version: string;
  title: string;
  author: string;
  release_version: string;
  generated_utc: string;
  observatory_sha256: string;
  source_count: number;
  update_policy: string;
}
