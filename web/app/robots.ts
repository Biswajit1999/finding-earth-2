import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/" },
    sitemap: "https://biswajit1999.github.io/finding-earth-2/sitemap.xml",
  };
}
