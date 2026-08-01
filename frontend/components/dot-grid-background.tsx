"use client";

import { useEffect, useRef } from "react";
import { useTheme } from "next-themes";

const SPACING = 26;
const DOT_RADIUS = 1.6;
const PUSH_RADIUS = 140;
const MAX_PUSH = 32;
const EASE = 0.16;

interface Dot {
  baseX: number;
  baseY: number;
  x: number;
  y: number;
}

export function DotGridBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const dotColor = resolvedTheme === "dark" ? "228, 228, 231" : "24, 24, 27";

    let dots: Dot[] = [];
    let pointer = { x: -9999, y: -9999, active: false };
    let raf = 0;
    let width = 0;
    let height = 0;

    function buildGrid() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = canvas!.parentElement?.clientWidth ?? window.innerWidth;
      height = canvas!.parentElement?.clientHeight ?? window.innerHeight;
      canvas!.width = width * dpr;
      canvas!.height = height * dpr;
      canvas!.style.width = `${width}px`;
      canvas!.style.height = `${height}px`;
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);

      const cols = Math.ceil(width / SPACING) + 1;
      const rows = Math.ceil(height / SPACING) + 1;
      dots = [];
      for (let row = 0; row < rows; row++) {
        for (let col = 0; col < cols; col++) {
          const x = col * SPACING;
          const y = row * SPACING;
          dots.push({ baseX: x, baseY: y, x, y });
        }
      }
    }

    function draw() {
      ctx!.clearRect(0, 0, width, height);
      ctx!.fillStyle = `rgba(${dotColor}, 0.5)`;
      for (const dot of dots) {
        let targetX = dot.baseX;
        let targetY = dot.baseY;
        if (pointer.active) {
          const dx = dot.baseX - pointer.x;
          const dy = dot.baseY - pointer.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < PUSH_RADIUS) {
            const force = (1 - dist / PUSH_RADIUS) * MAX_PUSH;
            const angle = Math.atan2(dy, dx);
            targetX = dot.baseX + Math.cos(angle) * force;
            targetY = dot.baseY + Math.sin(angle) * force;
          }
        }
        dot.x += (targetX - dot.x) * EASE;
        dot.y += (targetY - dot.y) * EASE;

        ctx!.beginPath();
        ctx!.arc(dot.x, dot.y, DOT_RADIUS, 0, Math.PI * 2);
        ctx!.fill();
      }
      raf = requestAnimationFrame(draw);
    }

    function drawStatic() {
      ctx!.clearRect(0, 0, width, height);
      ctx!.fillStyle = `rgba(${dotColor}, 0.5)`;
      for (const dot of dots) {
        ctx!.beginPath();
        ctx!.arc(dot.baseX, dot.baseY, DOT_RADIUS, 0, Math.PI * 2);
        ctx!.fill();
      }
    }

    function handleMove(e: MouseEvent) {
      const rect = canvas!.getBoundingClientRect();
      pointer = { x: e.clientX - rect.left, y: e.clientY - rect.top, active: true };
    }

    function handleLeave() {
      pointer.active = false;
    }

    function handleResize() {
      buildGrid();
      if (reduceMotion) drawStatic();
    }

    buildGrid();
    window.addEventListener("resize", handleResize);
    window.addEventListener("mousemove", handleMove);
    window.addEventListener("pointermove", handleMove);
    window.addEventListener("mouseleave", handleLeave);
    window.addEventListener("pointerleave", handleLeave);

    if (reduceMotion) {
      drawStatic();
    } else {
      raf = requestAnimationFrame(draw);
    }

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("mouseleave", handleLeave);
      window.removeEventListener("pointerleave", handleLeave);
    };
  }, [resolvedTheme]);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none absolute inset-0"
      aria-hidden="true"
    />
  );
}
