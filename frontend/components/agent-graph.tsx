"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { AgentGraphEdge, RosterAgent } from "@/lib/types";
import { api } from "@/lib/api";
import { DIVISION_COLOR, DIVISION_ORDER } from "@/lib/graph-data";

// Top-down layout: one row per division (CLAUDE.md roster order), agents
// laid out left-to-right within their row.
const COL_GAP = 230; // horizontal pitch between node slots within a row
const ROW_GAP = 130; // vertical pitch between division rows
const NODE_WIDTH = 178;
const NODE_HEIGHT = 54;
const PADDING = 40;
// Extra clearance above the first row so it doesn't sit under the
// top-left legend / top-right caption overlays.
const PADDING_TOP = 90;

const statusColor = (agent?: RosterAgent) => {
  if (!agent || !agent.built) return "var(--border)";
  if (agent.status === "error") return "var(--destructive)";
  if (agent.status === "turn_limit" || agent.status === "not_run") return "var(--warning)";
  return "var(--success)";
};

interface LayoutNode {
  name: string;
  division: string;
  x: number;
  y: number;
  agent?: RosterAgent;
}

type Selection = { kind: "node"; node: LayoutNode } | { kind: "edge"; edge: AgentGraphEdge } | null;

export function AgentGraph({ roster }: { roster: RosterAgent[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [edges, setEdges] = useState<AgentGraphEdge[]>([]);
  const [selected, setSelected] = useState<Selection>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [transform, setTransform] = useState({ x: 0, y: 0, k: 1 });
  const panState = useRef({ dragging: false, startX: 0, startY: 0, ox: 0, oy: 0 });
  const autoFitDone = useRef(false);

  useEffect(() => {
    api
      .agentsGraph()
      .then((g) => setEdges(g.edges))
      .catch(() => setEdges([]));
  }, []);

  // Structured pipeline layout: one row per division (CLAUDE.md roster
  // order), agents laid out left-to-right within their row, centered so
  // small divisions (e.g. one-agent Manufacturing) don't hug the left edge.
  const nodes: LayoutNode[] = useMemo(() => {
    const byDivision = new Map<string, RosterAgent[]>();
    roster.forEach((a) => {
      if (!byDivision.has(a.division)) byDivision.set(a.division, []);
      byDivision.get(a.division)!.push(a);
    });
    const maxCols = Math.max(1, ...Array.from(byDivision.values()).map((v) => v.length));
    const rowWidth = maxCols * COL_GAP;

    const out: LayoutNode[] = [];
    DIVISION_ORDER.forEach((division, rowIndex) => {
      const agents = byDivision.get(division) ?? [];
      const startX = PADDING + (rowWidth - agents.length * COL_GAP) / 2;
      agents.forEach((agent, colIndex) => {
        out.push({
          name: agent.name,
          division,
          x: startX + colIndex * COL_GAP,
          y: PADDING_TOP + rowIndex * ROW_GAP,
          agent,
        });
      });
    });
    return out;
  }, [roster]);

  // Top-down layout is taller than it is wide (up to 8 division rows), so
  // it won't fit the wide-but-short container at scale 1 the way the old
  // left-right layout did. Fit the whole real graph into view once, on
  // load — never overrides a pan/zoom the user did afterward. Waits for a
  // real, non-zero container size via ResizeObserver rather than measuring
  // on mount: a plain getBoundingClientRect() in the first effect tick can
  // catch the container mid-layout (e.g. width still 0, height still at its
  // min-h fallback), which silently produced scale(0) — an invisible graph.
  useEffect(() => {
    if (autoFitDone.current || nodes.length === 0 || !containerRef.current) return;
    const el = containerRef.current;
    const fit = (rect: { width: number; height: number }) => {
      if (autoFitDone.current || rect.width === 0 || rect.height === 0) return;
      const minX = Math.min(...nodes.map((n) => n.x));
      const maxX = Math.max(...nodes.map((n) => n.x + NODE_WIDTH));
      const minY = Math.min(...nodes.map((n) => n.y));
      const maxY = Math.max(...nodes.map((n) => n.y + NODE_HEIGHT));
      const contentW = maxX - minX + PADDING * 2;
      const contentH = maxY - minY + PADDING * 2;
      const k = Math.min(rect.width / contentW, rect.height / contentH, 1);
      const tx = (rect.width - contentW * k) / 2 - minX * k + PADDING * k;
      const ty = (rect.height - contentH * k) / 2 - minY * k + PADDING * k;
      setTransform({ x: tx, y: ty, k });
      autoFitDone.current = true;
    };
    const initial = el.getBoundingClientRect();
    if (initial.width > 0 && initial.height > 0) {
      fit(initial);
      return;
    }
    const observer = new ResizeObserver(([entry]) => fit(entry.contentRect));
    observer.observe(el);
    return () => observer.disconnect();
  }, [nodes]);

  const nodeByName = useMemo(() => {
    const m = new Map<string, LayoutNode>();
    nodes.forEach((n) => m.set(n.name, n));
    return m;
  }, [nodes]);

  const connected = useMemo(() => {
    if (!hovered) return null;
    const set = new Set<string>([hovered]);
    edges.forEach((e) => {
      if (e.source === hovered) set.add(e.target);
      if (e.target === hovered) set.add(e.source);
    });
    return set;
  }, [hovered, edges]);

  const onBgPointerDown = (e: React.PointerEvent) => {
    if ((e.target as SVGElement).dataset.bg !== "true") return;
    panState.current = { dragging: true, startX: e.clientX, startY: e.clientY, ox: transform.x, oy: transform.y };
    setSelected(null);
  };
  const onPointerMove = (e: React.PointerEvent) => {
    if (!panState.current.dragging) return;
    setTransform((t) => ({
      ...t,
      x: panState.current.ox + (e.clientX - panState.current.startX),
      y: panState.current.oy + (e.clientY - panState.current.startY),
    }));
  };
  const onPointerUp = () => {
    panState.current.dragging = false;
  };
  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 0.92 : 1.08;
    setTransform((t) => ({ ...t, k: Math.min(2.5, Math.max(0.35, t.k * factor)) }));
  };

  function edgePath(source: LayoutNode, target: LayoutNode): string {
    const sx = source.x + NODE_WIDTH / 2;
    const sy = source.y + NODE_HEIGHT;
    const tx = target.x + NODE_WIDTH / 2;
    const ty = target.y;
    const dy = ty - sy;
    // Backward/same-row edges (dy small or negative) bow outward instead
    // of collapsing into a line straight through other nodes.
    const bow = Math.max(60, Math.abs(dy) * 0.5);
    return `M ${sx} ${sy} C ${sx} ${sy + bow}, ${tx} ${ty - bow}, ${tx} ${ty}`;
  }

  return (
    <div
      ref={containerRef}
      className="relative h-[calc(100vh-11rem)] min-h-[480px] w-full select-none overflow-hidden rounded-lg bg-card"
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerLeave={onPointerUp}
      onWheel={onWheel}
    >
      <svg width="100%" height="100%" onPointerDown={onBgPointerDown} className="cursor-grab active:cursor-grabbing">
        <defs>
          <marker id="agent-graph-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--muted-foreground)" />
          </marker>
        </defs>
        <rect data-bg="true" x={0} y={0} width="100%" height="100%" fill="transparent" />
        <g transform={`translate(${transform.x} ${transform.y}) scale(${transform.k})`}>
          <g>
            {edges.map((e, i) => {
              const source = nodeByName.get(e.source);
              const target = nodeByName.get(e.target);
              if (!source || !target) return null;
              const dim = connected && (!connected.has(e.source) || !connected.has(e.target));
              const isSelected = selected?.kind === "edge" && selected.edge === e;
              return (
                <path
                  key={i}
                  d={edgePath(source, target)}
                  fill="none"
                  stroke={isSelected ? "var(--brand)" : "var(--border-strong,var(--border))"}
                  strokeWidth={isSelected ? 2.25 : 1.25}
                  opacity={dim ? 0.08 : isSelected ? 1 : 0.55}
                  markerEnd="url(#agent-graph-arrow)"
                  className="cursor-pointer"
                  onClick={(ev) => {
                    ev.stopPropagation();
                    setSelected({ kind: "edge", edge: e });
                  }}
                />
              );
            })}
          </g>
          <g>
            {nodes.map((n) => {
              const dim = connected && !connected.has(n.name);
              const built = n.agent?.built;
              const isSelected = selected?.kind === "node" && selected.node.name === n.name;
              return (
                <g
                  key={n.name}
                  transform={`translate(${n.x} ${n.y})`}
                  opacity={dim ? 0.3 : 1}
                  onMouseEnter={() => setHovered(n.name)}
                  onMouseLeave={() => setHovered((h) => (h === n.name ? null : h))}
                  onClick={(ev) => {
                    ev.stopPropagation();
                    setSelected({ kind: "node", node: n });
                  }}
                  className="cursor-pointer"
                >
                  <rect
                    width={NODE_WIDTH}
                    height={NODE_HEIGHT}
                    rx={8}
                    fill="var(--card)"
                    stroke={isSelected ? "var(--brand)" : DIVISION_COLOR[n.division] ?? "var(--border)"}
                    strokeWidth={isSelected ? 2 : built ? 1.5 : 1}
                    strokeDasharray={built ? undefined : "3 3"}
                  />
                  <foreignObject x={10} y={4} width={NODE_WIDTH - 18} height={NODE_HEIGHT - 8}>
                    <div
                      style={{
                        width: "100%",
                        height: "100%",
                        display: "flex",
                        flexDirection: "column",
                        justifyContent: "center",
                        opacity: built ? 0.92 : 0.55,
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 0 }}>
                        <span
                          style={{
                            width: 7,
                            height: 7,
                            borderRadius: 999,
                            background: statusColor(n.agent),
                            flexShrink: 0,
                          }}
                        />
                        <span
                          className="text-[length:var(--text-xs)] font-medium text-foreground"
                          style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", minWidth: 0 }}
                        >
                          {n.name}
                        </span>
                      </div>
                      <span
                        className="text-[length:var(--text-2xs)] text-muted-foreground"
                        style={{ marginLeft: 13, marginTop: 2 }}
                      >
                        {built ? `${n.agent!.run_count} run${n.agent!.run_count === 1 ? "" : "s"}` : "not built"}
                      </span>
                    </div>
                  </foreignObject>
                </g>
              );
            })}
          </g>
        </g>
      </svg>

      <div className="pointer-events-none absolute left-4 top-4 flex flex-col gap-1.5">
        {DIVISION_ORDER.map((division) => (
          <div key={division} className="flex items-center gap-1.5 text-[length:var(--text-2xs)] text-muted-foreground">
            <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: DIVISION_COLOR[division] }} />
            {division}
          </div>
        ))}
      </div>

      <div className="pointer-events-none absolute right-4 top-4 max-w-[240px] text-right text-[length:var(--text-2xs)] text-muted-foreground">
        Edges are real — reconstructed from which agents&apos; actual runs referenced the same baseline or requirement, not a prescribed diagram.
      </div>

      {selected?.kind === "node" && (
        <div className="absolute bottom-4 left-4 w-80 rounded-lg border border-border bg-popover p-4 shadow-lg">
          <div className="mb-1 flex items-start justify-between gap-2">
            <span className="text-[length:var(--text-base)] font-semibold">{selected.node.name}</span>
            <button
              onClick={() => setSelected(null)}
              className="text-muted-foreground transition-colors hover:text-foreground"
              aria-label="Close"
            >
              ×
            </button>
          </div>
          <p className="text-[length:var(--text-2xs)] text-muted-foreground">{selected.node.division}</p>
          {selected.node.agent?.built ? (
            <>
              <p className="mt-2.5 max-h-40 overflow-y-auto text-[length:var(--text-xs)] leading-[1.6] text-muted-foreground">
                {selected.node.agent.latest_output ?? "No run yet."}
              </p>
              <p className="mt-2.5 text-[length:var(--text-2xs)] text-muted-foreground">
                {selected.node.agent.run_count} run{selected.node.agent.run_count === 1 ? "" : "s"}
                {selected.node.agent.error_count > 0 && ` · ${selected.node.agent.error_count} errored`}
              </p>
            </>
          ) : (
            <p className="mt-2.5 text-[length:var(--text-xs)] text-muted-foreground">Not built yet.</p>
          )}
        </div>
      )}

      {selected?.kind === "edge" && (
        <div className="absolute bottom-4 left-4 w-80 rounded-lg border border-border bg-popover p-4 shadow-lg">
          <div className="mb-1 flex items-start justify-between gap-2">
            <span className="text-[length:var(--text-sm)] font-semibold">
              {selected.edge.source} → {selected.edge.target}
            </span>
            <button
              onClick={() => setSelected(null)}
              className="text-muted-foreground transition-colors hover:text-foreground"
              aria-label="Close"
            >
              ×
            </button>
          </div>
          <p className="mt-2 text-[length:var(--text-2xs)] font-semibold uppercase tracking-[0.06em] text-muted-foreground">
            Real shared artifacts
          </p>
          <ul className="mt-1.5 space-y-1">
            {selected.edge.artifacts.map((a) => (
              <li key={a} className="font-mono text-[length:var(--text-xs)] text-foreground">
                {a}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
