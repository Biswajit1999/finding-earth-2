export function PageHeader({
  eyebrow,
  title,
  lede,
  meta,
  children,
}: {
  eyebrow: string;
  title: string;
  lede?: string;
  meta?: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="border-b border-[var(--color-line)]">
      <div className="mx-auto max-w-[1400px] px-4 pb-10 pt-12 sm:px-6 sm:pt-16">
        <div className="rule-label mb-4">
          <span className="eyebrow">{eyebrow}</span>
        </div>
        <h1 className="max-w-[22ch] text-[length:var(--text-display)] font-light leading-[1.03]">
          {title}
        </h1>
        {lede && (
          <p className="mt-5 max-w-[68ch] text-[15px] leading-relaxed text-[var(--color-dim)]">
            {lede}
          </p>
        )}
        {meta && (
          <p className="mt-4 font-[family-name:var(--font-mono)] text-[11px] text-[var(--color-muted)]">
            {meta}
          </p>
        )}
        {children}
      </div>
    </header>
  );
}

/**
 * A caveat block. Used wherever the interface must qualify what a reader is
 * looking at — an extrapolated model, an unvalidated fit, a visualisation that
 * is not an image.
 */
export function Caveat({
  tone = "warn",
  title,
  children,
}: {
  tone?: "warn" | "info" | "stop";
  title?: string;
  children: React.ReactNode;
}) {
  const colour =
    tone === "stop"
      ? "var(--color-rose)"
      : tone === "info"
        ? "var(--color-cyan)"
        : "var(--color-gold)";
  return (
    <aside
      className="border-l-2 py-2.5 pl-4"
      style={{ borderColor: colour }}
      role="note"
    >
      {title && (
        <p
          className="font-[family-name:var(--font-mono)] text-[11px] uppercase tracking-[0.1em]"
          style={{ color: colour }}
        >
          {title}
        </p>
      )}
      <div className="mt-1 text-[13px] leading-relaxed text-[var(--color-dim)]">
        {children}
      </div>
    </aside>
  );
}

export function StatBlock({
  value,
  label,
  sub,
  tone = "var(--color-ivory)",
}: {
  value: string;
  label: string;
  sub?: string;
  tone?: string;
}) {
  return (
    <div className="border-l border-[var(--color-line-strong)] pl-3.5">
      <p
        className="font-[family-name:var(--font-mono)] text-[1.5rem] leading-none tabular-nums"
        style={{ color: tone }}
      >
        {value}
      </p>
      <p className="mt-1.5 text-[12px] font-medium leading-tight text-[var(--color-dim)]">
        {label}
      </p>
      {sub && (
        <p className="mt-0.5 text-[11px] leading-tight text-[var(--color-muted)]">{sub}</p>
      )}
    </div>
  );
}

/**
 * Figure wrapper enforcing the project's chart contract: every chart carries a
 * caption, its units, and where its data came from.
 */
export function Figure({
  title,
  caption,
  source,
  method,
  children,
  wide = false,
}: {
  title: string;
  caption?: string;
  source?: string;
  method?: string;
  children: React.ReactNode;
  wide?: boolean;
}) {
  return (
    <figure className={`panel p-5 ${wide ? "" : ""}`}>
      <figcaption className="mb-4">
        <h3 className="font-[family-name:var(--font-sans)] text-[14px] font-semibold text-[var(--color-ivory)]">
          {title}
        </h3>
        {caption && (
          <p className="mt-1.5 max-w-[76ch] text-[12.5px] leading-relaxed text-[var(--color-muted)]">
            {caption}
          </p>
        )}
      </figcaption>
      <div className="overflow-x-auto">{children}</div>
      {(source || method) && (
        <p className="mt-3 border-t border-[var(--color-line)] pt-2.5 font-[family-name:var(--font-mono)] text-[10.5px] leading-relaxed text-[var(--color-faint)]">
          {source && <>Source: {source}. </>}
          {method && <>Method: {method}.</>}
        </p>
      )}
    </figure>
  );
}
