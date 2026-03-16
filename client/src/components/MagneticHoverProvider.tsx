"use client";

import { useEffect } from "react";

const MAGNETIC_SELECTOR = 'button, a[class*="rounded"][class*="bg-"]';

function resetMagnetic(el: HTMLElement | null) {
  if (!el) return;
  el.style.setProperty("--mx", "0px");
  el.style.setProperty("--my", "0px");
}

export default function MagneticHoverProvider() {
  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const supportsFinePointer = window.matchMedia("(pointer: fine)").matches;
    if (!supportsFinePointer) {
      return;
    }

    let active: HTMLElement | null = null;

    const onPointerMove = (ev: PointerEvent) => {
      const target = (ev.target as Element | null)?.closest(MAGNETIC_SELECTOR) as HTMLElement | null;

      if (target !== active) {
        resetMagnetic(active);
        active = target;
      }

      if (!active) {
        return;
      }

      const rect = active.getBoundingClientRect();
      if (!rect.width || !rect.height) {
        return;
      }

      const nx = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
      const ny = ((ev.clientY - rect.top) / rect.height) * 2 - 1;
      const mx = Math.max(-1, Math.min(1, nx)) * 2;
      const my = Math.max(-1, Math.min(1, ny)) * 2;

      active.style.setProperty("--mx", `${mx.toFixed(2)}px`);
      active.style.setProperty("--my", `${my.toFixed(2)}px`);
    };

    const onPointerDown = (ev: PointerEvent) => {
      const target = (ev.target as Element | null)?.closest(MAGNETIC_SELECTOR) as HTMLElement | null;
      if (target) {
        target.style.setProperty("--mx", "0px");
        target.style.setProperty("--my", "0px");
      }
    };

    const onWindowBlur = () => {
      resetMagnetic(active);
      active = null;
    };

    window.addEventListener("pointermove", onPointerMove, { passive: true });
    window.addEventListener("pointerdown", onPointerDown, { passive: true });
    window.addEventListener("blur", onWindowBlur);

    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("blur", onWindowBlur);
      resetMagnetic(active);
    };
  }, []);

  return null;
}
