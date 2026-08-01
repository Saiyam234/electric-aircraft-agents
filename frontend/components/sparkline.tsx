"use client";

import { motion } from "framer-motion";
import { useId } from "react";

export function Sparkline({
  values,
  width = 520,
  height = 64,
  className,
}: {
  values: number[];
  width?: number;
  height?: number;
  className?: string;
}) {
  const gradientId = useId();
  if (values.length < 2) return null;

  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const span = hi - lo || 1;
  const n = values.length;
  const pad = 3;

  const points = values.map((v, i) => {
    const x = (i / (n - 1)) * width;
    const y = height - ((v - lo) / span) * (height - pad * 2) - pad;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const line = points.join(" ");
  const area = `0,${height} ${line} ${width},${height}`;
  const gridLines = [0.25, 0.5, 0.75].map((f) => height * f);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      style={{ width: "100%", height, display: "block", overflow: "visible" }}
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--brand)" stopOpacity="0.16" />
          <stop offset="100%" stopColor="var(--brand)" stopOpacity="0" />
        </linearGradient>
      </defs>

      {gridLines.map((y) => (
        <line
          key={y}
          x1={0}
          y1={y}
          x2={width}
          y2={y}
          stroke="var(--border)"
          strokeWidth={1}
          vectorEffect="non-scaling-stroke"
        />
      ))}

      <motion.polygon
        points={area}
        fill={`url(#${gradientId})`}
        stroke="none"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      />
      <motion.polyline
        points={line}
        fill="none"
        stroke="var(--brand)"
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
      />
    </svg>
  );
}
