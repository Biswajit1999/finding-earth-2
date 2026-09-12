import type { Metadata } from "next";

import { MissionObservatory } from "@/components/observatory/MissionObservatory";
import { Caveat, PageHeader, StatBlock } from "@/components/PageHeader";
import { getObservatory } from "@/lib/data";

export const metadata: Metadata = { title: "Mission Observatory", description: "Mission-specific evidence views for JWST, HWO, ANDES, PLATO, Gaia and Roman, with observation and forecast status separated." };

export default function MissionsPage() {
  const data = getObservatory().missions;
  const observed = data.missions.filter((mission) => mission.labels_present.includes("OBSERVED")).length;
  return <>
    <PageHeader eyebrow="Exoearth evidence observatory · missions" title="Different observatories answer different questions" lede="JWST, HWO, ANDES, PLATO, Gaia and Roman are not interchangeable rows in one score. Each desk states what the mission can measure, what evidence is public now, and where a forecast begins." meta={`Status checked ${data.status_as_of} · six versioned adapters`} />
    <section className="mx-auto max-w-[1400px] px-4 py-14 sm:px-6 sm:py-20"><div className="grid gap-8 sm:grid-cols-2 xl:grid-cols-4"><StatBlock value={String(data.missions.length)} label="mission desks" sub="separate scientific roles"/><StatBlock value={String(observed)} label="with observed evidence" sub="current public products"/><StatBlock value={String(data.missions.length - observed)} label="forecast-only or mixed" sub="status remains visible"/><StatBlock value={data.status_as_of} label="status date" sub="official sources checked"/></div><div className="mt-10"><Caveat title="Separation policy">{data.separation_policy}</Caveat></div></section>
    <div className="border-y border-[var(--color-line)] bg-[var(--color-deep)]"><MissionObservatory missions={data.missions} details={data.details} /></div>
  </>;
}

