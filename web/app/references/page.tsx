import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { getReferences } from "@/lib/data";
import { compactInt } from "@/lib/format";

export const metadata: Metadata = {
  title: "References",
  description: "Full bibliography, compiled from per-measurement archive reference links.",
};

const KEY_CITATIONS = [
  {
    text: "Kopparapu, R. K., Ramirez, R., Kasting, J. F. et al. (2013). Habitable Zones Around Main-Sequence Stars: New Estimates. ApJ, 765(2), 131.",
    doi: "10.1088/0004-637X/765/2/131",
  },
  {
    text: "Kopparapu, R. K. et al. (2013). Erratum: Habitable Zones Around Main-Sequence Stars: New Estimates. ApJ, 770(1), 82.",
    doi: "10.1088/0004-637X/770/1/82",
  },
  {
    text: "Schulze-Makuch, D., Méndez, A., Fairén, A. G. et al. (2011). A Two-Tiered Approach to Assessing the Habitability of Exoplanets. Astrobiology, 11(10), 1041–1052.",
    doi: "10.1089/ast.2010.0592",
  },
  {
    text: "Rogers, L. A. (2015). Most 1.6 Earth-Radius Planets are not Rocky. ApJ, 801(1), 41.",
    doi: "10.1088/0004-637X/801/1/41",
  },
  {
    text: "Fulton, B. J., Petigura, E. A., Howard, A. W. et al. (2017). The California-Kepler Survey III: A Gap in the Radius Distribution of Small Planets. AJ, 154(3), 109.",
    doi: "10.3847/1538-3881/aa80eb",
  },
  {
    text: "Kempton, E. M.-R., Bean, J. L., Louie, D. R. et al. (2018). A Framework for Prioritizing the TESS Planetary Candidates Most Amenable to Atmospheric Characterization. PASP, 130(993), 114401.",
    doi: "10.1088/1538-3873/aadf6f",
  },
  {
    text: "Kopp, G., & Lean, J. L. (2011). A new, lower value of total solar irradiance. Geophysical Research Letters, 38(1), L01706.",
    doi: "10.1029/2010GL045777",
  },
  {
    text: "Buchschacher, N., Ségransan, D., Udry, S., Diaz, R. (2015). DACE: Data Analysis Center for Exoplanets. ASP Conference Series, 495, 7.",
    doi: null,
  },
];

export default function ReferencesPage() {
  const { references, n_distinct_publications, n_measurement_links } = getReferences();

  return (
    <>
      <PageHeader
        eyebrow="Bibliography"
        title="References"
        lede={`Every methodological citation, plus ${compactInt(n_distinct_publications)} distinct publications traced from ${compactInt(n_measurement_links)} per-measurement reference links the NASA Exoplanet Archive attaches to its composite parameters.`}
      />

      <div className="mx-auto max-w-[1400px] px-4 py-10 sm:px-6">
        <section className="mb-14">
          <h2 className="mb-4 font-[family-name:var(--font-display)] text-xl font-medium">
            Key methodological citations
          </h2>
          <ol className="space-y-3">
            {KEY_CITATIONS.map((c, i) => (
              <li key={i} className="flex gap-3 text-[13px] leading-relaxed text-[var(--color-dim)]">
                <span className="font-[family-name:var(--font-mono)] text-[var(--color-muted)]">
                  [{i + 1}]
                </span>
                <span>
                  {c.text}{" "}
                  {c.doi && (
                    <a
                      href={"https://doi.org/" + c.doi}
                      target="_blank"
                      rel="noreferrer"
                      className="link"
                    >
                      doi:{c.doi}
                    </a>
                  )}
                </span>
              </li>
            ))}
          </ol>
        </section>

        <section>
          <h2 className="mb-1 font-[family-name:var(--font-display)] text-xl font-medium">
            Measurement-source bibliography
          </h2>
          <p className="mb-4 text-[13px] text-[var(--color-muted)]">
            Publications behind individual catalogue measurements, ranked by
            how many measurements in this analysis trace to them.
          </p>
          <div className="panel overflow-x-auto">
            <table className="data-table min-w-[720px]">
              <caption className="sr-only">Publications by number of measurements sourced</caption>
              <thead>
                <tr>
                  <th scope="col">Reference</th>
                  <th scope="col">Bibcode</th>
                  <th scope="col" className="text-right">Measurements</th>
                </tr>
              </thead>
              <tbody>
                {references.slice(0, 200).map((r, i) => (
                  <tr key={i}>
                    <td>
                      {r.reference_url ? (
                        <a href={r.reference_url} target="_blank" rel="noreferrer" className="link">
                          {r.reference_label}
                        </a>
                      ) : (
                        r.reference_label
                      )}
                    </td>
                    <td className="font-[family-name:var(--font-mono)] text-[11px] text-[var(--color-muted)]">
                      {r.bibcode ?? "—"}
                    </td>
                    <td className="text-right font-[family-name:var(--font-mono)] tabular-nums">
                      {compactInt(r.n_measurements)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {references.length > 200 && (
            <p className="mt-3 text-[11.5px] text-[var(--color-muted)]">
              Showing the top 200 of {compactInt(references.length)} distinct
              sources. Full list in{" "}
              <code>results/measurement_provenance.csv.gz</code>.
            </p>
          )}
        </section>
      </div>
    </>
  );
}
