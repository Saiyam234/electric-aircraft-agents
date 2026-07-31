"use client";

import { motion } from "framer-motion";

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
  if (values.length < 2) return null;

  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const span = hi - lo || 1;
  const n = values.length;

  const points = values.map((v, i) => {
    const x = (i / (n - 1)) * width;
    const y = height - ((v - lo) / span) * (height - 5) - 2.5;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const line = points.join(" ");

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      style={{ width: "100%", height, display: "block" }}
      preserveAspectRatio="none"
    >
      <motion.polyline
        points={line}
        fill="none"
        stroke="var(--brand)"
        strokeWidth={1.75}
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
      />
    </svg>
  );
}
