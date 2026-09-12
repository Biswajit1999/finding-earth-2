import type { Metadata, Viewport } from "next";
import "./globals.css";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { getObservatoryRelease, getSummary } from "@/lib/data";

const SITE_URL = "https://biswajit1999.github.io/finding-earth-2/";
const REPOSITORY_URL = "https://github.com/Biswajit1999/finding-earth-2";

function buildDescription(): string {
  const summary = getSummary();
  const records = summary.scale.total_source_records.toLocaleString("en-GB");
  const planets = summary.population.n_confirmed_planets.toLocaleString("en-GB");

  return `Finding Earth 2.0 in Distant Worlds is an open-source exoplanet research project by Biswajit Jana analysing ${records} public astronomical archive records and ${planets} confirmed planets using habitable-zone models, Earth Similarity Index, Monte Carlo uncertainty, transit, radial-velocity and atmospheric spectroscopy data.`;
}

export function generateMetadata(): Metadata {
  const description = buildDescription();

  return {
    metadataBase: new URL(SITE_URL),
    applicationName: "Finding Earth 2.0",
    title: {
      default: "Finding Earth 2.0 in Distant Worlds",
      template: "%s — Finding Earth 2.0",
    },
    description,
    keywords: [
      "Finding Earth 2.0",
      "Earth 2.0",
      "Earth-like exoplanets",
      "potentially habitable exoplanets",
      "habitable zone",
      "Earth Similarity Index",
      "exoplanet habitability",
      "NASA Exoplanet Archive",
      "Gaia DR3",
      "TESS exoplanets",
      "Kepler exoplanets",
      "exoplanet spectroscopy",
      "radial velocity exoplanets",
      "transit photometry",
      "computational astrophysics",
      "reproducible astronomy",
    ],
    authors: [
      {
        name: "Biswajit Jana",
        url: "https://github.com/Biswajit1999",
      },
    ],
    creator: "Biswajit Jana",
    publisher: "Biswajit Jana",
    category: "Astronomy and Astrophysics",
    openGraph: {
      type: "website",
      url: SITE_URL,
      locale: "en_GB",
      title: "Finding Earth 2.0 in Distant Worlds",
      description,
      siteName: "Finding Earth 2.0",
      images: [
        {
          url: `${SITE_URL}figures/hz_diagram.png`,
          alt: "Finding Earth 2.0 habitable-zone analysis of confirmed exoplanets",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: "Finding Earth 2.0 in Distant Worlds",
      description,
      images: [`${SITE_URL}figures/hz_diagram.png`],
    },
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
        "max-image-preview": "large",
        "max-snippet": -1,
        "max-video-preview": -1,
      },
    },
  };
}

export const viewport: Viewport = {
  themeColor: "#07090e",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const summary = getSummary();
  const observatoryRelease = getObservatoryRelease();
  const description = buildDescription();

  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "WebSite",
        "@id": `${SITE_URL}#website`,
        url: SITE_URL,
        name: "Finding Earth 2.0 in Distant Worlds",
        alternateName: [
          "Finding Earth 2.0",
          "Earth 2.0 exoplanet search",
        ],
        description,
        inLanguage: "en",
        author: { "@id": `${SITE_URL}#author` },
        sameAs: REPOSITORY_URL,
      },
      {
        "@type": "Person",
        "@id": `${SITE_URL}#author`,
        name: "Biswajit Jana",
        url: "https://github.com/Biswajit1999",
        sameAs: ["https://github.com/Biswajit1999"],
      },
      {
        "@type": "Dataset",
        "@id": `${SITE_URL}#dataset`,
        name: "Finding Earth 2.0 candidate ranking",
        url: SITE_URL,
        description,
        creator: { "@id": `${SITE_URL}#author` },
        dateModified: summary.generated_utc,
        isPartOf: { "@id": `${SITE_URL}#website` },
        keywords: [
          "exoplanets",
          "Earth-like planets",
          "habitable zone",
          "Earth Similarity Index",
          "NASA Exoplanet Archive",
          "Gaia DR3",
          "Monte Carlo uncertainty propagation",
          "transit photometry",
          "radial velocity",
          "atmospheric spectroscopy",
        ],
        variableMeasured: [
          "Earth Similarity Index",
          "Habitable-zone membership probability",
          "Observational confidence",
          "Earth-2.0 candidate index",
          "Planet radius",
          "Planet mass",
          "Incident stellar flux",
          "Equilibrium temperature",
        ],
        measurementTechnique: [
          "Public astronomical archive crossmatch",
          "Monte Carlo uncertainty propagation",
          "Habitable-zone climate-model evaluation",
          "Transit analysis",
          "Radial-velocity analysis",
          "Atmospheric spectroscopy metadata analysis",
        ],
      },
    ],
  };

  return (
    <html
      lang="en"
      suppressHydrationWarning
    >
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,400;9..144,500;9..144,600&family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
        <link rel="sitemap" type="application/xml" href={`${SITE_URL}sitemap.xml`} />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c"),
          }}
        />
        <script
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
        <SiteHeader bundledHash={observatoryRelease.observatory_sha256} />
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
