"use client";

import { useEffect, useRef } from "react";

type NodePoint = {
  x: number;
  y: number;
  vx: number;
  vy: number;
};

const NODE_COUNT_DESKTOP = 95;
const NODE_COUNT_MOBILE = 55;
const CONNECT_DISTANCE = 145;
const SPEED_LIMIT = 0.65;
const CURSOR_RADIUS = 240;
const CURSOR_FORCE = 0.14;
const NODE_HOVER_RADIUS = 8;

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

export default function InteractiveNetworkBg() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvasEl = canvasRef.current;
    if (!canvasEl) {
      return;
    }

    const context = canvasEl.getContext("2d", { alpha: true });
    if (!context) {
      return;
    }

    const canvas = canvasEl;
    const ctx = context;

    const dpr = window.devicePixelRatio || 1;
    let width = 0;
    let height = 0;
    let animationId = 0;
    let running = true;

    const mouse = {
      x: -9999,
      y: -9999,
      active: false,
    };

    let nodes: NodePoint[] = [];

    function resize() {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      const targetCount = width < 900 ? NODE_COUNT_MOBILE : NODE_COUNT_DESKTOP;
      nodes = Array.from({ length: targetCount }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * SPEED_LIMIT,
        vy: (Math.random() - 0.5) * SPEED_LIMIT,
      }));
    }

    function updateNodes() {
      for (const node of nodes) {
        const jitterX = (Math.random() - 0.5) * 0.02;
        const jitterY = (Math.random() - 0.5) * 0.02;
        node.vx = clamp(node.vx + jitterX, -SPEED_LIMIT, SPEED_LIMIT);
        node.vy = clamp(node.vy + jitterY, -SPEED_LIMIT, SPEED_LIMIT);

        if (mouse.active) {
          const dx = mouse.x - node.x;
          const dy = mouse.y - node.y;
          const distSq = dx * dx + dy * dy;
          const radius = CURSOR_RADIUS;
          if (distSq < radius * radius) {
            const dist = Math.max(1, Math.sqrt(distSq));
            const force = (radius - dist) / radius;
            // Repel nodes from the pointer for clear interaction response.
            node.vx -= (dx / dist) * force * CURSOR_FORCE;
            node.vy -= (dy / dist) * force * CURSOR_FORCE;
          }
        }

        node.x += node.vx;
        node.y += node.vy;

        if (node.x <= 0 || node.x >= width) {
          node.vx *= -1;
          node.x = clamp(node.x, 0, width);
        }
        if (node.y <= 0 || node.y >= height) {
          node.vy *= -1;
          node.y = clamp(node.y, 0, height);
        }
      }
    }

    function draw() {
      ctx.clearRect(0, 0, width, height);

      let hoveredNodeIndex = -1;
      if (mouse.active) {
        let bestDistSq = Number.POSITIVE_INFINITY;
        for (let i = 0; i < nodes.length; i += 1) {
          const node = nodes[i];
          const dx = mouse.x - node.x;
          const dy = mouse.y - node.y;
          const distSq = dx * dx + dy * dy;
          if (distSq <= NODE_HOVER_RADIUS * NODE_HOVER_RADIUS && distSq < bestDistSq) {
            bestDistSq = distSq;
            hoveredNodeIndex = i;
          }
        }
      }

      const connectedNodes = new Set<number>();
      if (hoveredNodeIndex >= 0) {
        connectedNodes.add(hoveredNodeIndex);
        const hoveredNode = nodes[hoveredNodeIndex];
        for (let i = 0; i < nodes.length; i += 1) {
          if (i === hoveredNodeIndex) {
            continue;
          }
          const node = nodes[i];
          const dx = hoveredNode.x - node.x;
          const dy = hoveredNode.y - node.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist <= CONNECT_DISTANCE) {
            connectedNodes.add(i);
          }
        }
      }

      const gradient = ctx.createLinearGradient(0, 0, width, height);
      gradient.addColorStop(0, "rgba(10, 21, 56, 0.82)");
      gradient.addColorStop(1, "rgba(7, 16, 38, 0.82)");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);

      for (let i = 0; i < nodes.length; i += 1) {
        const a = nodes[i];

        for (let j = i + 1; j < nodes.length; j += 1) {
          const b = nodes[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist > CONNECT_DISTANCE) {
            continue;
          }

          const alpha = (1 - dist / CONNECT_DISTANCE) * 0.32;
          ctx.strokeStyle = `rgba(108, 154, 230, ${alpha})`;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }

      for (let i = 0; i < nodes.length; i += 1) {
        const node = nodes[i];

        if (hoveredNodeIndex >= 0 && i === hoveredNodeIndex) {
          ctx.fillStyle = "rgba(255, 126, 126, 0.98)";
          ctx.fillRect(node.x - 4.4, node.y - 4.4, 8.8, 8.8);
          continue;
        }

        if (connectedNodes.has(i)) {
          ctx.fillStyle = "rgba(255, 118, 118, 0.9)";
          ctx.fillRect(node.x - 3.1, node.y - 3.1, 6.2, 6.2);
          continue;
        }

        ctx.fillStyle = "rgba(237, 88, 88, 0.72)";
        ctx.fillRect(node.x - 1.7, node.y - 1.7, 3.4, 3.4);
      }

    }

    function tick() {
      if (!running) {
        return;
      }
      updateNodes();
      draw();
      animationId = window.requestAnimationFrame(tick);
    }

    function onMouseMove(event: MouseEvent) {
      mouse.x = event.clientX;
      mouse.y = event.clientY;
      mouse.active = true;
    }

    function onTouchMove(event: TouchEvent) {
      if (!event.touches || event.touches.length === 0) {
        return;
      }
      const touch = event.touches[0];
      mouse.x = touch.clientX;
      mouse.y = touch.clientY;
      mouse.active = true;
    }

    function onMouseLeave() {
      mouse.active = false;
      mouse.x = -9999;
      mouse.y = -9999;
    }

    resize();
    tick();

    window.addEventListener("resize", resize);
    window.addEventListener("mousemove", onMouseMove, { passive: true });
    window.addEventListener("touchmove", onTouchMove, { passive: true });
    window.addEventListener("mouseleave", onMouseLeave);

    return () => {
      running = false;
      window.cancelAnimationFrame(animationId);
      window.removeEventListener("resize", resize);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("touchmove", onTouchMove);
      window.removeEventListener("mouseleave", onMouseLeave);
    };
  }, []);

  return <canvas ref={canvasRef} className="pointer-events-none fixed inset-0 z-0" aria-hidden="true" />;
}
