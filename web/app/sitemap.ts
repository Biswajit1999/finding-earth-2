import type { MetadataRoute } from "next";

import { getAllPlanetSlugs, getSummary } from "@/lib/data";

export const dynamic = "force-static";

const SITE_ROOT = "https://biswajit1999.github.io/finding-earth-2";

const coreRoutes = [
  "",
  "about",
  "atlas",
  "beyond",
  "atmospheres",
  "climate",
  "compare",
  "data",
  "follow-up",
  "falsification",
  "galaxy",
  "limitations",
  "methods",
  "missions",
  "model-sensitivity",
  "occurrence",
  "population",
  "perspective",
  "ranking",
  "references",
  "research",
  "selection",
  "stellar-environment",
  "information-gain",
  "hwo",
  "evidence",
  "rv-lab",
  "spectral-lab",
  "transit-lab",
  "universe",
] as const;

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date(getSummary().generated_utc);

  const core: MetadataRoute.Sitemap = coreRoutes.map((route) => ({
    url: route ? `${SITE_ROOT}/${route}/` : `${SITE_ROOT}/`,
    lastModified,
  }));

  const candidates: MetadataRoute.Sitemap = getAllPlanetSlugs().map((slug) => ({
    url: `${SITE_ROOT}/candidate/${slug}/`,
    lastModified,
  }));

  return [...core, ...candidates];
}
