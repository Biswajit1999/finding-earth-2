import Image from "next/image";

import { assetPath } from "@/lib/assets";

/**
 * A generated scientific figure with its caption doing the labelling —
 * matching paper/main.tex, where the same title-less image set is used
 * because a caption sitting right underneath makes an in-image title
 * redundant. `src` is a path under public/figures/.
 */
export function ArticleFigure({
  src,
  width,
  height,
  alt,
  caption,
}: {
  src: string;
  width: number;
  height: number;
  alt: string;
  caption: React.ReactNode;
}) {
  return (
    <figure className="not-prose my-8">
      <Image
        src={assetPath(src)}
        width={width}
        height={height}
        alt={alt}
        sizes="(min-width: 1180px) 720px, calc(100vw - 2rem)"
        className="w-full rounded-[var(--radius-md)] border border-[var(--color-line)]"
      />
      <figcaption className="mt-2.5 text-[13px] leading-relaxed text-[var(--color-muted)]">
        {caption}
      </figcaption>
    </figure>
  );
}
