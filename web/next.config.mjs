/** @type {import('next').NextConfig} */

// Static export: the whole site is pre-rendered to HTML/JS/JSON and can be
// served by GitHub Pages with no server. The scientific pipeline runs in Python
// ahead of the build, so there is nothing for a backend to do at request time.
//
// BASE_PATH lets the same build serve from a repository subpath
// (user.github.io/finding-earth-2) or from a domain root.
const basePath = process.env.BASE_PATH ?? '';

const nextConfig = {
  output: 'export',
  basePath,
  assetPrefix: basePath || undefined,
  trailingSlash: true,
  images: {
    // next/image's optimiser needs a server; a static export cannot use it.
    unoptimized: true,
  },
  env: {
    NEXT_PUBLIC_BASE_PATH: basePath,
  },
  reactStrictMode: true,
  // Pin the workspace root: without it Turbopack walks up past the repository
  // and picks a lockfile from the user's home directory.
  turbopack: {
    root: import.meta.dirname,
  },
};

export default nextConfig;
