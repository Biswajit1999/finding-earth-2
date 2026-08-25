import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { Caveat } from "@/components/PageHeader";
import { TransitLab } from "@/components/labs/TransitLab";
import { getTransitValidation } from "@/lib/data";

export const metadata: Metadata = {
  title: "Transit Lab",
  description:
    "Real MAST light curves, detrended and fitted, validated against published transit depths.",
};

export default function TransitLabPage() {
  const data = getTransitValidation();

  return (
    <>
      <PageHeader
        eyebrow="Photometry"
        title="Transit Lab"
        lede="Public light curves retrieved from MAST, detrended with a Savitzky-Golay filter, folded on the published ephemeris and fitted with a trapezoid. Every fit is checked against the published depth before it is called validated."
      />
      <div className="mx-auto max-w-[1400px] px-4 pt-6 sm:px-6">
        <Caveat tone="warn" title="None of the top Earth-2.0 candidates appear here">
          None of the top-ranked candidates produces a validated transit fit: six
          of the top ten were detected by radial velocity and are not transiting,
          and the four that do transit orbit faint M dwarfs whose TESS
          photometry cannot resolve their shallow transits. The targets below are
          bright hot Jupiters and sub-Neptunes chosen to demonstrate that the
          pipeline itself works, not because they are habitable.
        </Caveat>
      </div>
      {data ? (
        <TransitLab data={data} />
      ) : (
        <div className="mx-auto max-w-[1400px] px-4 py-8 text-[13px] text-[var(--color-muted)] sm:px-6">
          Transit validation data is not available in this build.
        </div>
      )}
    </>
  );
}
