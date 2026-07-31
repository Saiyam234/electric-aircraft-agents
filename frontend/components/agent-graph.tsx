"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCenter,
  forceCollide,
  type Simulation,
  type SimulationNodeDatum,
} from "d3-force";
import type { RosterAgent } from "@/lib/types";
import { GRAPH_EDGES, DIVISION_COLOR } from "@/lib/graph-data";

interface Node extends SimulationNodeDatum {
  id: string;
  division: string;
  agent?: RosterAgent;
}
interface Link {
  source: Node;
  target: Node;
}

const statusColor = (agent?: RosterAgent) => {
  if (!agent || !agent.built) return "var(--border-strong,var(--border))";
  if (agent.status === "error") return "var(--destructive)";
  if (agent.status === "turn_limit" || agent.status === "not_run") return "var(--warning)";
  return "var(--success)";
};

export function AgentGraph({ roster }: { roster: RosterAgent[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 800, h: 600 });
  const [nodes, setNodes] = useState<Node[]>([]);
  const linksRef = useRef<Link[]>([]);
  const simRef = useRef<Simulation<Node, undefined> | null>(null);
  const [selected, setSelected] = useState<Node | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [transform, setTransform] = useState({ x: 0, y: 0, k: 1 });
  const panState = useRef<{ dragging: boolean; startX: number; startY: number; ox: number; oy: number }>({
    dragging: false,
    startX: 0,
    startY: 0,
    ox: 0,
    oy: 0,
  });
  const dragNodeId = useRef<string | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const ro = new ResizeObserver((entries) => {
      const r = entries[0].contentRect;
      setSize({ w: r.width, h: r.height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (roster.length === 0 || size.w === 0) return;

    const nodeMap = new Map<string, Node>();
    roster.forEach((agent) => {
      nodeMap.set(agent.name, { id: agent.name, division: agent.division, agent });
    });

    const links: Link[] = GRAPH_EDGES.filter(
      ([a, b]) => nodeMap.has(a) && nodeMap.has(b)
    ).map(([a, b]) => ({ source: nodeMap.get(a)!, target: nodeMap.get(b)! }));
    linksRef.current = links;

    const nodeList = Array.from(nodeMap.values());

    const sim = forceSimulation(nodeList)
      .force(
        "link",
        forceLink<Node, Link>(links)
          .id((d) => d.id)
          .distance(90)
          .strength(0.5)
      )
      .force("charge", forceManyBody().strength(-220))
      .force("center", forceCenter(size.w / 2, size.h / 2))
      .force("collide", forceCollide(30))
      .alphaDecay(0.02);

    simRef.current = sim;
    sim.on("tick", () => setNodes([...nodeList]));

    return () => {
      sim.stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roster, size.w, size.h]);

  const connected = useMemo(() => {
    if (!hovered) return null;
    const set = new Set<string>([hovered]);
    linksRef.current.forEach((l) => {
      if (l.source.id === hovered) set.add(l.target.id);
      if (l.target.id === hovered) set.add(l.source.id);
    });
    return set;
  }, [hovered]);

  const onBgPointerDown = (e: React.PointerEvent) => {
    if ((e.target as SVGElement).dataset.bg !== "true") return;
    panState.current = {
      dragging: true,
      startX: e.clientX,
      startY: e.clientY,
      ox: transform.x,
      oy: transform.y,
    };
    setSelected(null);
  };
  const onPointerMove = (e: React.PointerEvent) => {
    if (dragNodeId.current) {
      const rect = containerRef.current!.getBoundingClientRect();
      const x = (e.clientX - rect.left - transform.x) / transform.k;
      const y = (e.clientY - rect.top - transform.y) / transform.k;
      const n = nodes.find((n) => n.id === dragNodeId.current);
      if (n) {
        n.fx = x;
        n.fy = y;
        simRef.current?.alpha(0.3).restart();
      }
      return;
    }
    if (panState.current.dragging) {
      setTransform((t) => ({
        ...t,
        x: panState.current.ox + (e.clientX - panState.current.startX),
        y: panState.current.oy + (e.clientY - panState.current.startY),
      }));
    }
  };
  const onPointerUp = () => {
    panState.current.dragging = false;
    if (dragNodeId.current) {
      const n = nodes.find((n) => n.id === dragNodeId.current);
      if (n) {
        n.fx = null;
        n.fy = null;
      }
      dragNodeId.current = null;
    }
  };
  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 0.92 : 1.08;
    setTransform((t) => ({ ...t, k: Math.min(2.5, Math.max(0.4, t.k * factor)) }));
  };

  return (
    <div
      ref={containerRef}
      className="relative h-[calc(100vh-11rem)] min-h-[480px] w-full select-none overflow-hidden rounded-lg bg-card"
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerLeave={onPointerUp}
      onWheel={onWheel}
    >
      <svg
        width={size.w}
        height={size.h}
        onPointerDown={onBgPointerDown}
        className="cursor-grab active:cursor-grabbing"
      >
        <rect data-bg="true" x={0} y={0} width={size.w} height={size.h} fill="transparent" />
        <g transform={`translate(${transform.x} ${transform.y}) scale(${transform.k})`}>
          {linksRef.current.map((l, i) => {
            const dim = connected && (!connected.has(l.source.id) || !connected.has(l.target.id));
            const bothBuilt = l.source.agent?.built && l.target.agent?.built;
            return (
              <line
                key={i}
                x1={l.source.x}
                y1={l.source.y}
                x2={l.target.x}
                y2={l.target.y}
                stroke="var(--border-strong,var(--border))"
                strokeWidth={bothBuilt ? 1.1 : 0.75}
                strokeDasharray={bothBuilt ? undefined : "2 3"}
                opacity={dim ? 0.08 : bothBuilt ? 0.55 : 0.28}
              />
            );
          })}
          {nodes.map((n) => {
            const dim = connected && !connected.has(n.id);
            const r = n.agent?.built ? 6 : 4;
            return (
              <g
                key={n.id}
                transform={`translate(${n.x ?? 0} ${n.y ?? 0})`}
                opacity={dim ? 0.25 : 1}
                onPointerDown={(e) => {
                  e.stopPropagation();
                  dragNodeId.current = n.id;
                }}
                onMouseEnter={() => setHovered(n.id)}
                onMouseLeave={() => setHovered((h) => (h === n.id ? null : h))}
                onClick={(e) => {
                  e.stopPropagation();
                  setSelected(n);
                }}
                className="cursor-pointer"
              >
                <circle
                  r={r}
                  fill={n.agent?.built ? statusColor(n.agent) : "var(--card)"}
                  stroke={DIVISION_COLOR[n.division] ?? "var(--border)"}
                  strokeWidth={n.agent?.built ? 0 : 1.3}
                />
                <text
                  x={r + 6}
                  y={3}
                  fontSize={11}
                  fill="var(--foreground)"
                  opacity={n.agent?.built ? 0.85 : 0.5}
                  style={{ fontFamily: "var(--font-geist-sans)" }}
                >
                  {n.id}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      {selected && (
        <div className="absolute bottom-4 left-4 w-80 rounded-lg border border-border bg-popover p-4 shadow-lg">
          <div className="mb-1 flex items-start justify-between gap-2">
            <span className="text-[length:var(--text-base)] font-semibold">{selected.id}</span>
            <button
              onClick={() => setSelected(null)}
              className="text-muted-foreground hover:text-foreground"
              aria-label="Close"
            >
              ×
            </button>
          </div>
          <p className="text-[length:var(--text-2xs)] text-muted-foreground">{selected.division}</p>
          {selected.agent?.built ? (
            <>
              <p className="mt-2.5 max-h-40 overflow-y-auto text-[length:var(--text-xs)] leading-[1.6] text-muted-foreground">
                {selected.agent.latest_output ?? "No run yet."}
              </p>
              <p className="mt-2.5 text-[length:var(--text-2xs)] text-muted-foreground">
                {selected.agent.run_count} run{selected.agent.run_count === 1 ? "" : "s"}
                {selected.agent.error_count > 0 && ` · ${selected.agent.error_count} errored`}
              </p>
            </>
          ) : (
            <p className="mt-2.5 text-[length:var(--text-xs)] text-muted-foreground">Not built yet.</p>
          )}
        </div>
      )}

      <div className="pointer-events-none absolute right-4 top-4 text-[length:var(--text-2xs)] text-muted-foreground">
        Edges are the intended pipeline per CLAUDE.md — not live messaging
      </div>
    </div>
  );
}
