import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { SpectralLab } from "@/components/labs/SpectralLab";
import { getSpectraIndex, getSummary } from "@/lib/data";
import { compactInt } from "@/lib/format";

export const metadata: Metadata = {
  title: "Spectral Lab",
  description:
    "Published transmission and emission spectra of exoplanet atmospheres from the NASA Exoplanet Archive.",
};

export default function SpectralLabPage() {
  const index = getSpectraIndex();
  const summary = getSummary();
  const nPlanets = summary.atmosphere["planets_with_transmission_spectra"];

  return (
    <>
      <PageHeader
        eyebrow="Atmospheric spectroscopy"
        title="Spectral Lab"
        lede={`Real, published transmission spectra of planetary atmospheres — genuine per-bandpass transit-depth measurements, not stellar spectra. ${compactInt(index.filter((r) => r.kind === "transmission").length)} of the ${nPlanets} planets with published transmission spectra have four or more usable points and are browsable here.`}
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
            by this code.
          </p>
        </div>
      </div>
      <SpectralLab index={index} />
    </>
  );
}
