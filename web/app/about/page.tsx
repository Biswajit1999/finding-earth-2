import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { getSummary } from "@/lib/data";

export const metadata: Metadata = {
  title: "About",
  description: "About the Finding Earth 2.0 project and its author.",
};

export default function AboutPage() {
  const s = getSummary();

  return (
    <>
      <PageHeader eyebrow="Project" title="About" />
      <div className="mx-auto max-w-[1400px] px-4 py-10 sm:px-6">
        <div className="prose-sci mx-auto">
          <h2>The project</h2>
          <p>
            Finding Earth 2.0 in Distant Worlds is a reproducible, open-source
            computational astrophysics project: it ingests real public
            astronomical archives, propagates measurement uncertainty
            correctly, and ranks exoplanet candidates on interpretable,
            physically motivated criteria — presented through an interactive
            research interface rather than a static report.
          </p>
          <p>
            It is not a decorative space website, a toy machine-learning demo,
            or a static list of known planets. Every number displayed anywhere
            on this site is produced by the Python analysis pipeline in the
            repository, from data retrieved live from public archives, and
            traceable back to the archive row and publication that produced it.
          </p>

          <h2>Author</h2>
          <p>
            <strong>Biswajit Jana</strong> — repository owner and author.{" "}
            <a
              href="https://github.com/Biswajit1999"
              className="link"
              target="_blank"
              rel="noreferrer"
            >
              github.com/Biswajit1999
            </a>
          </p>

          <h2>Licence</h2>
          <p>
            The software in this repository is MIT-licensed. The astronomical
            datasets it retrieves remain governed by their originating
            archives — see{" "}
            <Link href="/data" className="link">
              Data sources
            </Link>{" "}
            for full acknowledgement text.
          </p>

          <h2>This build</h2>
          <p className="font-[family-name:var(--font-mono)] text-[12.5px]">
            earth2 v{s.earth2_version} · analysis generated{" "}
            {new Date(s.generated_utc).toISOString().slice(0, 16).replace("T", " ")} UTC
            · Python {s.software?.python} · runtime {s.runtime_seconds}s
          </p>

          <h2>Source</h2>
          <p>
            <a
              href="https://github.com/Biswajit1999/finding-earth-2"
              className="link"
              target="_blank"
              rel="noreferrer"
            >
              github.com/Biswajit1999/finding-earth-2
            </a>
          </p>
        </div>
      </div>
    </>
  );
}
