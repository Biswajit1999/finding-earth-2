"use client";

import { useEffect, useState } from "react";

const LATEST = "https://raw.githubusercontent.com/Biswajit1999/finding-earth-2/main/web/public/data/release.json";

export function FreshnessPulse({ bundledHash }: { bundledHash: string }) {
  const [status, setStatus] = useState<"checking" | "current" | "newer" | "offline">("checking");

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${LATEST}?opened=${Date.now()}`, { cache: "no-store", signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("release snapshot unavailable");
        return response.json() as Promise<{ observatory_sha256?: string }>;
      })
      .then((latest) => {
        if (!latest.observatory_sha256) throw new Error("invalid release schema");
        setStatus(latest.observatory_sha256 === bundledHash ? "current" : "newer");
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setStatus("offline");
      });
    return () => controller.abort();
  }, [bundledHash]);

  const copy = {
    checking: "checking data",
    current: "verified snapshot",
    newer: "new release available",
    offline: "verified offline snapshot",
  }[status];
  const tone = status === "newer" ? "var(--color-gold)" : status === "offline" ? "var(--color-muted)" : "var(--color-cyan)";

  return (
    <span
      role="status"
      aria-live="polite"
      title="Checks the latest processed and committed research payload on GitHub whenever the site opens"
      className="hidden items-center gap-1.5 font-[family-name:var(--font-mono)] text-[9px] uppercase tracking-[0.1em] text-[var(--color-muted)] xl:inline-flex"
    >
      <span className="size-1.5 rounded-full" style={{ background: tone }} aria-hidden />
      {copy}
    </span>
  );
}

