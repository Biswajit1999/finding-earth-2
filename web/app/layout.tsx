import type { Metadata, Viewport } from "next";
import "./globals.css";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { getSummary } from "@/lib/data";

const DESCRIPTION =
  "A reproducible computational search for potentially Earth-like exoplanets, ranked from NASA Exoplanet Archive catalogues cross-matched against Gaia DR3, with selected MAST transit and DACE radial-velocity deep dives.";

export const metadata: Metadata = {
  metadataBase: new URL("https://biswajit1999.github.io/finding-earth-2/"),
  title: {
    default: "Finding Earth 2.0 in Distant Worlds",
    template: "%s — Finding Earth 2.0",
  },
  description: DESCRIPTION,
  keywords: [
    "exoplanets",
    "habitable zone",
    "astrobiology",
    "Earth similarity index",
    "NASA Exoplanet Archive",
    "reproducible research",
    "computational astrophysics",
  ],
  authors: [{ name: "Biswajit Jana", url: "https://github.com/Biswajit1999" }],
  creator: "Biswajit Jana",
  openGraph: {
    type: "website",
    title: "Finding Earth 2.0 in Distant Worlds",
    description: DESCRIPTION,
    siteName: "Finding Earth 2.0",
  },
  twitter: {
    card: "summary_large_image",
    title: "Finding Earth 2.0 in Distant Worlds",
    description: DESCRIPTION,
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: "#07090e",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const summary = getSummary();

  // Structured metadata describing the dataset this site publishes.
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    name: "Finding Earth 2.0 candidate ranking",
    description: DESCRIPTION,
    creator: { "@type": "Person", name: "Biswajit Jana" },
    // No `license` field: the MIT licence in this repository's LICENSE file
    // covers the analysis code only (see docs/DATA_SOURCES.md, "Software
    // licence vs. data licence"). The dataset described here is derived from
    // NASA Exoplanet Archive, MAST and DACE records, which remain governed by
    // their originating archives' own terms -- claiming MIT for the dataset
    // itself would misrepresent that.
    dateModified: summary.generated_utc,
    isBasedOn: summary.scale.archives,
    variableMeasured: [
      "Earth Similarity Index",
      "Habitable-zone membership probability",
      "Observational confidence",
      "Earth-2.0 candidate index",
    ],
  };

  return (
    <html
      lang="en"
      // The anti-FOUC script below sets data-theme on this element before
      // React hydrates, so the server-rendered markup (no attribute) and the
      // first client read (possibly "light") legitimately differ. That's the
      // point of the script, not a bug -- suppress only this element's
      // hydration warning rather than the mismatch check globally.
      suppressHydrationWarning
    >
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,400;9..144,500;9..144,600&family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
        <script
          type="application/ld+json"
          // JSON-LD must be injected as raw text; React has no other way to emit
          // it. The payload is built here from our own build-time analysis
          // output, never from user input, and `<` is escaped so no value can
          // close the script element early.
          dangerouslySetInnerHTML={{
            __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c"),
          }}
        />
        <script
          // Sets the theme attribute before first paint so a returning
          // visitor who chose light mode never sees a flash of the dark
          // default. Must run synchronously in <head>, before React
          // hydrates -- a useEffect in the toggle component would run one
          // frame too late.
          dangerouslySetInnerHTML={{
            __html:
              "try{if(localStorage.getItem('theme')==='light'){document.documentElement.setAttribute('data-theme','light')}}catch(e){}",
          }}
        />
      </head>
      <body>
        <a href="#main" className="skip-link">
          Skip to content
        </a>
        <SiteHeader />
        <main id="main">{children}</main>
        <SiteFooter
          generatedUtc={summary.generated_utc}
          version={summary.earth2_version}
          sourceRecords={summary.scale.total_source_records}
        />
      </body>
    </html>
  );
}
