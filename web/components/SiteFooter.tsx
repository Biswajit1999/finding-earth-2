import Link from "next/link";
import { compactInt, utcLabel } from "@/lib/format";

export function SiteFooter({
  generatedUtc,
  version,
  sourceRecords,
}: {
  generatedUtc: string;
  version: string;
  sourceRecords: number;
}) {
  return (
    <footer className="mt-24 border-t border-[var(--color-line)] bg-[var(--color-deep)]">
      <div className="mx-auto max-w-[1400px] px-4 py-12 sm:px-6">
        <div className="grid gap-10 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
          <div>
            <p className="font-[family-name:var(--font-display)] text-lg">
              Finding Earth 2.0 in Distant Worlds
            </p>
            <p className="mt-2 max-w-sm text-[13px] leading-relaxed text-[var(--color-muted)]">
              A reproducible, data-driven search for potentially Earth-like worlds
              across the public astronomical archives. Every number on this site is
              computed by the pipeline in this repository from data retrieved live
              from public archives.
            </p>
            <p className="mt-4 font-[family-name:var(--font-mono)] text-[11px] text-[var(--color-muted)]">
              <span className="text-[var(--color-dim)]">Data last synchronised</span>
              <br />
              {utcLabel(generatedUtc)}
              <br />
              <span className="text-[var(--color-dim)]">
                {compactInt(sourceRecords)} source records
              </span>{" "}
              · earth2 v{version}
            </p>
            <p className="mt-3 max-w-sm text-[11px] leading-relaxed text-[var(--color-faint)]">
              &ldquo;Synchronised&rdquo; means with continually maintained public
              catalogues. This site does not receive live telescope telemetry.
            </p>
          </div>

          <FooterCol
            title="Explore"
            links={[
              ["/universe", "Universe"],
              ["/atlas", "Candidate Atlas"],
              ["/ranking", "Ranking"],
              ["/compare", "Compare Worlds"],
            ]}
          />
          <FooterCol
            title="Laboratories"
            links={[
              ["/spectral-lab", "Spectral Lab"],
              ["/transit-lab", "Transit Lab"],
              ["/rv-lab", "RV Lab"],
              ["/follow-up", "Follow-up Lab"],
              ["/research", "Research article"],
            ]}
          />
          <FooterCol
            title="Method"
            links={[
              ["/methods", "Methods"],
              ["/data", "Data sources"],
              ["/limitations", "Limitations"],
              ["/references", "References"],
              ["/about", "About"],
            ]}
          />
        </div>

        <div className="mt-12 border-t border-[var(--color-line)] pt-6">
          <p className="text-[11px] leading-relaxed text-[var(--color-muted)]">
            This research has made use of the NASA Exoplanet Archive, operated by the
            California Institute of Technology under contract with NASA under the
            Exoplanet Exploration Program; the Mikulski Archive for Space Telescopes
            (MAST) at STScI; and the Data &amp; Analysis Center for Exoplanets (DACE)
            operated by the University of Geneva. Software is MIT-licensed. The
            datasets remain governed by their originating archives — see{" "}
            <Link href="/data" className="link">
              Data sources
            </Link>{" "}
            for full acknowledgements.
          </p>
          <p className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-[var(--color-muted)]">
            <span>© {new Date(generatedUtc).getUTCFullYear()} Biswajit Jana</span>
            <a
              href="https://github.com/Biswajit1999/finding-earth-2"
              target="_blank"
              rel="noreferrer noopener"
              className="link"
            >
              Repository
            </a>
            <span className="text-[var(--color-faint)]">
              No claim of life detection is made anywhere on this site.
            </span>
          </p>
        </div>
      </div>
    </footer>
  );
}

function FooterCol({
  title,
  links,
}: {
  title: string;
  links: [string, string][];
}) {
  return (
    <div>
      <p className="eyebrow mb-3">{title}</p>
      <ul className="space-y-1.5">
        {links.map(([href, label]) => (
          <li key={href}>
            <Link
              href={href}
              className="text-[13px] text-[var(--color-dim)] transition-colors hover:text-[var(--color-cyan)]"
            >
              {label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
