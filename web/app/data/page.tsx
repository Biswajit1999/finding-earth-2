import type { Metadata } from "next";
import { PageHeader } from "@/components/PageHeader";
import { getProvenance } from "@/lib/data";
import { compactInt, utcLabel } from "@/lib/format";
import type { DatasetManifestRow } from "@/lib/types";

export const metadata: Metadata = {
  title: "Data Sources",
  description: "Every archive, table, retrieval timestamp and licence behind this project.",
};

export default function DataPage() {
  const prov = getProvenance();
  const datasets: DatasetManifestRow[] = prov.datasets ?? [];

  return (
    <>
      <PageHeader
        eyebrow="Source trail"
        title="Data sources"
        lede="Every table retrieved, with the exact query, the retrieval timestamp, and a hash of the payload as received. Nothing here is a static download: re-running python -m earth2 sync reconstructs this list from the live archives."
        meta={`Last synchronised ${utcLabel(prov.sync_state?.last_sync_utc)} · ${compactInt(prov.total_source_records)} total source records`}
      />

      <div className="mx-auto max-w-[1400px] px-4 py-10 sm:px-6">
        <div className="panel overflow-x-auto">
          <table className="data-table min-w-[820px]">
            <caption className="sr-only">Retrieved archive datasets with source and retrieval details</caption>
            <thead>
              <tr>
                <th scope="col">Dataset</th>
                <th scope="col">Archive</th>
                <th scope="col">Table</th>
                <th scope="col" className="text-right">Rows</th>
                <th scope="col">Retrieved (UTC)</th>
                <th scope="col">Status</th>
                <th scope="col">DOI</th>
                <th scope="col">Payload SHA-256</th>
              </tr>
            </thead>
            <tbody>
              {datasets.map((d) => (
                <tr key={d.dataset_id}>
                  <td className="font-[family-name:var(--font-mono)] text-[11.5px]">{d.dataset_id}</td>
                  <td>{d.archive}</td>
                  <td className="font-[family-name:var(--font-mono)] text-[11.5px]">{d.source_table}</td>
                  <td className="text-right font-[family-name:var(--font-mono)] tabular-nums">
                    {compactInt(d.n_rows)}
                  </td>
                  <td className="font-[family-name:var(--font-mono)] text-[11px] text-[var(--color-muted)]">
                    {d.retrieved_utc?.slice(0, 16).replace("T", " ")}
                  </td>
                  <td>
                    <span
                      className={
                        d.status === "ok" ? "text-[var(--color-verdant)]" : "text-[var(--color-rose)]"
                      }
                    >
                      {d.status}
                    </span>
                  </td>
                  <td className="font-[family-name:var(--font-mono)] text-[11px]">{d.doi || "—"}</td>
                  <td className="font-[family-name:var(--font-mono)] text-[10.5px] text-[var(--color-muted)]">
                    {d.sha256_short}…
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="prose-sci mx-auto mt-14">
          <h2>Archives integrated</h2>

          <h3>NASA Exoplanet Archive</h3>
          <p>
            The analysis spine. Twelve tables: <code>pscomppars</code>{" "}
            (confirmed-planet composite parameters), <code>ps</code>{" "}
            (coherent per-publication parameter sets, used for reference
            counting, literature-spread checks, and comparison with the
            mixed-source composite),{" "}
            <code>toi</code>, <code>k2pandc</code>, and Kepler{" "}
            <code>q1_q17_dr25_koi</code> / <code>_tce</code> (candidates and
            detections, explicitly not counted as confirmed planets),{" "}
            <code>transitspec</code> / <code>emissionspec</code> (genuine
            atmospheric spectroscopy), <code>spectra</code> (spectrum-file
            index), <code>stellarhosts</code>, <code>ml</code>{" "}
            (microlensing), and <code>di_stars_exep</code>{" "}
            (direct-imaging targets). Column lists are validated against the
            live TAP schema before every query.
          </p>
          <p>
            Acknowledgement required by the archive: &ldquo;This research has
            made use of the NASA Exoplanet Archive, which is operated by the
            California Institute of Technology, under contract with the
            National Aeronautics and Space Administration under the Exoplanet
            Exploration Program.&rdquo;
          </p>

          <h3>MAST / STScI</h3>
          <p>
            Public TESS and Kepler light curves, retrieved via{" "}
            <code>lightkurve</code>&rsquo;s metadata-first search-then-download
            pattern. Never downloaded blindly; a target with no public product
            is reported as such.
          </p>

          <h3>DACE (University of Geneva)</h3>
          <p>
            Public radial-velocity time series via the official{" "}
            <code>dace-query</code> package, including the stellar activity
            indicators measured from the same spectra. Public data requires no
            authentication; this project never accesses private DACE holdings.
          </p>
          <p>
            Acknowledgement: Buchschacher, N., Segransan, D., Udry, S., Diaz, R.
            (2015), ASP Conference Series 495, 7.
          </p>

          <h2>What is deliberately NOT in this project</h2>
          <p>
            The ESO Science Archive was investigated but is not integrated in
            this release: it was not required to reach the ingested{" "}
            {compactInt(prov.total_source_records)} source records, and adding
            it without a clear scientific gain would inflate scale without
            inflating evidence. Gaia DR3 <em>is</em> integrated — see{" "}
            <code>gaia_dr3_crossmatch</code> in the table above — as an
            independent distance cross-check by exact Gaia{" "}
            <code>source_id</code>, matched against the archive&rsquo;s own
            recorded identifier rather than by sky coordinates, which risks
            silently pairing the wrong star in crowded fields. It is not a
            full astrometric re-reduction of the catalogue.
          </p>

          <h2>Raw payload policy</h2>
          <p>
            Raw archive payloads are never committed to the repository. They
            are large, they belong to the archives, and every one is
            byte-reconstructible from its manifest&rsquo;s exact query string
            via <code>python -m earth2 sync</code>. The manifests — including a
            SHA-256 of the payload as received — are committed, so archive
            drift (a value changing between syncs) is detectable rather than
            silent.
          </p>
        </div>
      </div>
    </>
  );
}
