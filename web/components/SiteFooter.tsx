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
      <div className="mx-auto max-w-[1400px] px-4 py-14 sm:px-6 sm:py-16">
        <div className="grid gap-12 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
          <div>
            <p className="font-[family-name:var(--font-display)] text-xl">
              Finding Earth 2.0 in Distant Worlds
            </p>
            <p className="mt-3 max-w-md text-[14px] leading-6 text-[var(--color-muted)]">
              A reproducible, data-driven search for potentially Earth-like worlds
              across the public astronomical archives. Every number on this site is
              computed by the pipeline in this repository from data retrieved live
              from public archives.
            </p>
            <p className="mt-5 font-[family-name:var(--font-mono)] text-[12px] leading-5 text-[var(--color-muted)]">
              <span className="text-[var(--color-dim)]">Data last synchronised</span>
              <br />
              {utcLabel(generatedUtc)}
              <br />
              <span className="text-[var(--color-dim)]">
                {compactInt(sourceRecords)} source records
              </span>{" "}
              · earth2 v{version}
            </p>
            <p className="mt-3 max-w-md text-[12px] leading-5 text-[var(--color-faint)]">
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

        <div className="mt-14 border-t border-[var(--color-line)] pt-8">
          <p className="mx-auto max-w-6xl text-center text-[12px] leading-6 text-[var(--color-muted)]">
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
          <div className="mt-8 flex flex-col items-center text-center">
            <p className="eyebrow">Created by</p>
            <p className="mt-2 font-[family-name:var(--font-display)] text-2xl text-[var(--color-ivory)]">
              Biswajit Jana
            </p>
            <nav
              aria-label="Author links"
              className="mt-4 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-[13px]"
            >
              <a
                href="https://github.com/Biswajit1999/finding-earth-2"
                target="_blank"
                rel="noreferrer noopener"
                className="link"
              >
                Repository
              </a>
              <a
                href="https://www.linkedin.com/in/biswajit-jana-27011a151/"
                target="_blank"
                rel="noreferrer noopener"
                className="link"
              >
                LinkedIn
              </a>
              <a
                href="https://biswajit1999.github.io/Biswajit_Jana.github.io/"
                target="_blank"
                rel="noreferrer noopener"
                className="link"
              >
                Portfolio
              </a>
            </nav>
            <p className="mt-5 text-[11.5px] leading-5 text-[var(--color-faint)]">
              © {new Date(generatedUtc).getUTCFullYear()} Biswajit Jana
              <span aria-hidden="true"> · </span>
              No claim of life detection is made anywhere on this site.
            </p>
          </div>
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
              className="text-[14px] leading-6 text-[var(--color-dim)] transition-colors hover:text-[var(--color-cyan)]"
            >
              {label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
