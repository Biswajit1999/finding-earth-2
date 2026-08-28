/**
 * Server-side data access.
 *
 * Every page in this site is statically pre-rendered, so data is read from the
 * filesystem at build time rather than fetched at runtime. That is what lets
 * the whole thing deploy to GitHub Pages with no backend, and it means the
 * numbers a reader sees are exactly the ones the Python pipeline produced for
 * that build.
 */

import { readFileSync, existsSync, readdirSync } from "node:fs";
import path from "node:path";

import { assetPath, BASE_PATH } from "./assets";
import { slugify } from "./format";
import type {
  CatalogueFile,
  CoverageRow,
  DeepDive,
  DeepDiveIndexEntry,
  Planet,
  ReferenceRow,
  SpectraIndexRow,
  SummaryFile,
  TransitValidationFile,
  UniverseFile,
} from "./types";

const DATA_DIR = path.join(process.cwd(), "public", "data");

function readJson<T>(name: string): T {
  const p = path.join(DATA_DIR, name);
  if (!existsSync(p)) {
    throw new Error(
      `Missing data product: ${name}. Run \`python -m earth2 export\` before building the site.`,
    );
  }
  return JSON.parse(readFileSync(p, "utf-8")) as T;
}

function readJsonOptional<T>(name: string): T | null {
  const p = path.join(DATA_DIR, name);
  if (!existsSync(p)) return null;
  return JSON.parse(readFileSync(p, "utf-8")) as T;
}

/* -------------------------------------------------------------------------
   Core products
   ------------------------------------------------------------------------- */
export function getSummary(): SummaryFile {
  return readJson<SummaryFile>("summary.json");
}

export function getCatalogueFile(): CatalogueFile {
  return readJson<CatalogueFile>("catalogue.json");
}

export function getUniverse(): UniverseFile {
  return readJson<UniverseFile>("universe.json");
}

export function getCoverage(): CoverageRow[] {
  const f = readJsonOptional<{ rows: CoverageRow[] }>("coverage.json");
  return f?.rows ?? [];
}

export function getReferences(): { references: ReferenceRow[]; n_distinct_publications: number; n_measurement_links: number; note: string } {
  return (
    readJsonOptional<any>("references.json") ?? {
      references: [],
      n_distinct_publications: 0,
      n_measurement_links: 0,
      note: "",
    }
  );
}

export function getProvenance(): any {
  return readJsonOptional<any>("provenance.json") ?? { datasets: [] };
}

export function getSpectraIndex(): SpectraIndexRow[] {
  const f = readJsonOptional<{ rows: SpectraIndexRow[] }>("spectra_index.json");
  return f?.rows ?? [];
}

export function getTransitValidation(): TransitValidationFile | null {
  return readJsonOptional<TransitValidationFile>("transit_validation.json");
}

export function getDeepDiveIndex(): DeepDiveIndexEntry[] {
  const f = readJsonOptional<{ systems: DeepDiveIndexEntry[] }>("deepdive_index.json");
  return (f?.systems ?? []).sort(
    (a, b) => (b.earth2_index ?? 0) - (a.earth2_index ?? 0),
  );
}

export function getDeepDive(slug: string): DeepDive | null {
  return readJsonOptional<DeepDive>(path.join("deepdive", `${slug}.json`));
}

export function listDeepDiveSlugs(): string[] {
  const dir = path.join(DATA_DIR, "deepdive");
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => f.replace(/\.json$/, ""));
}

/* -------------------------------------------------------------------------
   Columnar -> row materialisation

   The catalogue ships as one array per field to keep the payload small. This
   turns it back into objects for server-side rendering. The client-side atlas
   keeps the columnar form and indexes into it directly, because materialising
   6,000+ objects on every keystroke is exactly the cost the columnar format
   exists to avoid.
   ------------------------------------------------------------------------- */
export function materialisePlanets(file: CatalogueFile): Planet[] {
  const c = file.columns;
  const n = file.n_rows;
  const out: Planet[] = new Array(n);

  for (let i = 0; i < n; i++) {
    out[i] = {
      index: i,
      name: c.pl_name[i] ?? "",
      host: c.hostname[i] ?? "",
      rank: c.earth2_rank[i] ?? null,
      index_value: c.earth2_index[i] ?? null,
      similarity: c.score_earth_similarity[i] ?? null,
      habitability: c.score_conservative_habitability[i] ?? null,
      confidence: c.score_observational_confidence[i] ?? null,
      characterisation: c.score_characterisation_potential[i] ?? null,
      esi: c.esi_global_p50[i] ?? null,
      esiLo: c.esi_global_p16[i] ?? null,
      esiHi: c.esi_global_p84[i] ?? null,
      hzProb: c.hz_conservative_prob[i] ?? null,
      hzOptProb: c.hz_optimistic_prob[i] ?? null,
      hzConservative: c.hz_conservative[i] ?? null,
      hzExtrapolated: Boolean(c.hz_model_extrapolated[i]),
      rocky: c.rocky_plausibility[i] ?? null,
      rade: c.pl_rade[i] ?? null,
      radeLo: c.pl_rade_p16[i] ?? null,
      radeHi: c.pl_rade_p84[i] ?? null,
      mass: c.pl_bmasse[i] ?? null,
      massClass: c.mass_class[i] ?? null,
      density: c.pl_dens_used[i] ?? null,
      period: c.pl_orbper[i] ?? null,
      smax: c.pl_orbsmax[i] ?? null,
      ecc: c.pl_orbeccen[i] ?? null,
      insol: c.insol_used[i] ?? null,
      teq: c.teq_used[i] ?? null,
      teff: c.st_teff[i] ?? null,
      srad: c.st_rad[i] ?? null,
      smass: c.st_mass[i] ?? null,
      slum: c.st_lum[i] ?? null,
      spectype: c.st_spectype[i] ?? null,
      dist: c.sy_dist[i] ?? null,
      ra: c.ra[i] ?? null,
      dec: c.dec[i] ?? null,
      vmag: c.sy_vmag[i] ?? null,
      jmag: c.sy_jmag[i] ?? null,
      kmag: c.sy_kmag[i] ?? null,
      method: c.discoverymethod[i] ?? null,
      discYear: c.disc_year[i] ?? null,
      facility: c.disc_facility[i] ?? null,
      transits: c.tran_flag[i] === 1,
      rv: c.rv_flag[i] === 1,
      nRefs: c.n_references[i] ?? null,
      compositeSourceCount: c.composite_parameter_source_count?.[i] ?? null,
      compositeUsesMixedSources:
        c.composite_uses_mixed_sources?.[i] ?? null,
      defaultSolutionCoverage:
        c.default_solution_parameter_coverage?.[i] ?? null,
      compositeDefaultDifference:
        c.composite_default_median_fractional_difference?.[i] ?? null,
      uncCoverage: c.mc_uncertainty_coverage[i] ?? null,
      nTransmission: c.n_transmission_points[i] ?? null,
      nEmission: c.n_emission_points[i] ?? null,
      tsm: c.tsm[i] ?? null,
      rvK: c.rv_semi_amplitude_ms[i] ?? null,
      isControl: Boolean(c.is_control[i]),
      rankable: Boolean(c.rankable[i]),
    };
  }
  return out;
}

export function getPlanets(): Planet[] {
  return materialisePlanets(getCatalogueFile());
}

export function getTopCandidates(n = 20): Planet[] {
  return getPlanets()
    .filter((p) => !p.isControl && p.rankable && p.index_value !== null)
    .sort((a, b) => (b.index_value ?? 0) - (a.index_value ?? 0))
    .slice(0, n);
}

export function getControls(): Planet[] {
  return getPlanets().filter((p) => p.isControl);
}

/** Every non-control planet slug, for generateStaticParams. */
export function getAllPlanetSlugs(): string[] {
  return getPlanets()
    .filter((p) => !p.isControl)
    .map((p) => slugify(p.name));
}

export function getPlanetBySlug(slug: string): Planet | null {
  const planets = getPlanets();
  return planets.find((p) => slugify(p.name) === slug) ?? null;
}

/** Backwards-compatible exports for server-side consumers. */
export { BASE_PATH };
export const asset = assetPath;
