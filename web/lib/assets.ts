/**
 * Prefix a public asset with the repository base path used by GitHub Pages.
 *
 * `next/link` applies `basePath` automatically; `next/image`, `fetch`, and
 * ordinary asset URLs do not. Keeping that difference in one helper prevents
 * the production-only broken-image failure that occurs when a root-relative
 * `/figures/...` URL is deployed under `/finding-earth-2/`.
 */
export const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

export function assetPath(path: string): string {
  const absolute = path.startsWith("/") ? path : `/${path}`;
  return `${BASE_PATH}${absolute}`;
}
