/**
 * A margin note: one concrete number, instrument fact, or citation that
 * supports the adjacent prose without interrupting it. See .sidenote in
 * globals.css for how it escapes the narrow prose column into the page's
 * own gutter on wide screens, and folds back inline below that.
 */
export function SideNote({
  eyebrow,
  children,
  href,
  side = "right",
}: {
  eyebrow: string;
  children: React.ReactNode;
  href?: string;
  side?: "left" | "right";
}) {
  const className =
    "panel block p-3.5 text-[12px] leading-relaxed no-underline transition-colors" +
    (href ? " hover:border-[var(--color-cyan)]" : "") +
    (side === "left" ? " sidenote sidenote-left" : " sidenote");

  const content = (
    <>
      <p className="eyebrow mb-1.5">{eyebrow}</p>
      <div className="text-[var(--color-dim)]">{children}</div>
    </>
  );

  if (!href) {
    return <div className={className}>{content}</div>;
  }
  return (
    <a href={href} target="_blank" rel="noreferrer noopener" className={className}>
      {content}
    </a>
  );
}
