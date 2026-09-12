"use client";

import { useState } from "react";

interface GraphNode { id?: string; kind?: string; label?: string | null; name?: string; attributes?: Record<string, unknown>; }
interface Graph { root: string; nodes: GraphNode[]; edges: unknown[]; }

export function EvidenceExplorer({ examples }: { examples: Record<string, Graph[]> }) {
  const names = Object.keys(examples);
  const [name, setName] = useState(names[0] ?? "");
  const graph = examples[name]?.[0];
  if (!graph) return null;

  const kinds = [...new Set(graph.nodes.map((node) => node.kind ?? "record"))];
  return (
    <section className="mx-auto max-w-[1200px] px-4 py-16 sm:px-6 sm:py-20" aria-labelledby="evidence-explorer-title">
      <div className="grid gap-8 lg:grid-cols-[18rem_1fr]">
        <div>
          <p className="eyebrow text-[var(--color-cyan)]">Trace one quantity</p>
          <h2 id="evidence-explorer-title" className="mt-3 text-[length:var(--text-title)] font-light">From claim back to source</h2>
          <label className="mt-7 block text-xs text-[var(--color-dim)]">Example planet
            <select value={name} onChange={(event) => setName(event.target.value)} className="mt-2 min-h-11 w-full rounded-[var(--radius-sm)] border border-[var(--color-line-strong)] bg-[var(--color-panel)] px-3 text-sm text-[var(--color-ivory)]">{names.map((item) => <option key={item}>{item}</option>)}</select>
          </label>
          <p className="mt-5 font-[family-name:var(--font-mono)] text-[11px] text-[var(--color-muted)]">{graph.nodes.length} nodes · {graph.edges.length} directed links</p>
        </div>
        <div className="panel-raised overflow-hidden p-6 sm:p-8">
          <div className="flex flex-wrap gap-2">{kinds.map((kind) => <span key={kind} className="rounded-full border border-[var(--color-line-strong)] px-2 py-1 font-[family-name:var(--font-mono)] text-[9px] uppercase tracking-[0.1em] text-[var(--color-muted)]">{kind}</span>)}</div>
          <div className="mt-8 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {graph.nodes.slice(0, 18).map((node, index) => (
              <article key={node.id ?? index} className="relative rounded-[var(--radius-sm)] border border-[var(--color-line)] bg-[var(--color-panel)] p-4">
                <span aria-hidden className="absolute left-0 top-4 h-5 w-px bg-[var(--color-cyan)]" />
                <p className="eyebrow">{node.kind ?? "record"}</p>
                <p className="mt-2 [overflow-wrap:anywhere] text-xs leading-relaxed text-[var(--color-ivory)]">{node.name ?? node.label ?? node.id ?? "Evidence node"}</p>
                {node.attributes?.value !== undefined && <p className="mt-2 font-[family-name:var(--font-mono)] text-[10px] text-[var(--color-muted)]">{String(node.attributes.value)} {String(node.attributes.unit ?? "")}</p>}
              </article>
            ))}
          </div>
          {graph.nodes.length > 18 && <p className="mt-5 text-xs text-[var(--color-muted)]">Showing 18 of {graph.nodes.length} nodes. The complete machine-readable graph remains in the repository.</p>}
        </div>
      </div>
    </section>
  );
}
