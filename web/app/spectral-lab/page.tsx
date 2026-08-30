import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { SpectralLab } from "@/components/labs/SpectralLab";
import { getSpectraIndex, getSummary } from "@/lib/data";
import { compactInt } from "@/lib/format";
import { assetPath } from "@/lib/assets";

export const metadata: Metadata = {
  title: "Spectral Lab",
  description:
    "Published transmission and emission spectra of exoplanet atmospheres from the NASA Exoplanet Archive.",
};

export default function SpectralLabPage() {
  const index = getSpectraIndex();
  const summary = getSummary();
  const nPlanets = summary.atmosphere["planets_with_transmission_spectra"];
  const nEclipsePlanets = summary.atmosphere["planets_with_emission_spectra"];
  const plottedTransmission = index.filter((r) => r.kind === "transmission").length;
  const plottedEclipse = index.filter((r) => r.kind === "emission").length;
  const archived = summary.atmosphere["archived_spectrum_files_by_type"] as Record<
    string,
    number
  >;

  return (
    <>
      <PageHeader
        eyebrow="Atmospheric spectroscopy"
        title="Spectral Lab"
        lede={`Real, published spectra of planetary atmospheres: transmission during transit and thermal emission measured during secondary eclipse. ${compactInt(plottedTransmission)} of ${nPlanets} transmission planets and ${compactInt(plottedEclipse)} of ${nEclipsePlanets} eclipse planets have four or more usable points and are browsable here.`}
      />
      <div className="mx-auto max-w-[1400px] px-4 pt-6 sm:px-6">
        <div className="panel border-l-2 border-[var(--color-rose)] p-4">
          <p className="text-[13px] leading-relaxed text-[var(--color-dim)]">
            <strong className="text-[var(--color-ivory)]">
              A line near a molecular band is not a detection.
            </strong>{" "}
            Dashed overlays mark where a species is known to absorb, drawn for
            annotation only. Whether a feature at that wavelength constitutes
            evidence for that species is a question for the peer-reviewed
            analysis cited alongside each spectrum, not for a band overlay drawn
            by this project. Transmission and eclipse depths remain separate
            because they measure different observing geometries.
          </p>
        </div>
        <div className="mt-4 grid gap-px overflow-hidden border border-[var(--color-line)] bg-[var(--color-line)] sm:grid-cols-3">
          {[
            ["Transmission files", archived.Transmission ?? 0],
            ["Eclipse files", archived.Eclipse ?? 0],
            ["Direct-imaging files", archived["Direct Imaging"] ?? 0],
          ].map(([label, value]) => (
            <div key={String(label)} className="bg-[var(--color-panel)] px-4 py-3">
              <p className="font-[family-name:var(--font-mono)] text-xl text-[var(--color-ivory)]">
                {compactInt(Number(value))}
              </p>
              <p className="mt-1 text-[11px] text-[var(--color-muted)]">{label}</p>
            </div>
          ))}
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-[12px]">
          <a
            href={assetPath("/data/atmospheric_spectra_archive_index.csv")}
            download
            className="text-[var(--color-cyan)] underline decoration-[var(--color-line-strong)] underline-offset-4"
          >
            Download all 1,826 archive-file records (CSV)
          </a>
          <a
            href="https://exoplanetarchive.ipac.caltech.edu/cgi-bin/atmospheres/nph-firefly?atmospheres"
            target="_blank"
            rel="noreferrer"
            className="text-[var(--color-dim)] underline decoration-[var(--color-line-strong)] underline-offset-4"
          >
            Open the live NASA archive table ↗
          </a>
        </div>
      </div>
      <SpectralLab index={index} />
    </>
  );
}
