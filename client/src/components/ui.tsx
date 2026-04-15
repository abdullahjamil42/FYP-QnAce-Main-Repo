import type { ReactNode } from "react";

type CardProps = {
  children: ReactNode;
  className?: string;
};

export function GlassCard({ children, className = "" }: CardProps) {
  return (
    <article className={`card-glow rounded-2xl border border-white/20 bg-white/5 p-5 shadow-xl shadow-black/25 backdrop-blur-md ${className}`}>
      {children}
    </article>
  );
}

type BadgeProps = {
  children: ReactNode;
  tone?: "default" | "success" | "warning";
};

export function Badge({ children, tone = "default" }: BadgeProps) {
  const toneClass =
    tone === "success"
      ? "bg-emerald-500/20 text-emerald-200"
      : tone === "warning"
        ? "bg-amber-500/20 text-amber-100"
        : "bg-slate-300/15 text-slate-100";

  return <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${toneClass}`}>{children}</span>;
}

type ProgressProps = {
  label: string;
  value: number;
  hint?: string;
};

export function ProgressRow({ label, value, hint }: ProgressProps) {
  const safeValue = Math.max(0, Math.min(100, value));

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="text-qace-muted">{label}</span>
        <span className="font-semibold text-white">{safeValue.toFixed(0)}</span>
      </div>
      <div className="h-2 rounded-full bg-white/10">
        <div className="h-2 rounded-full bg-gradient-to-r from-qace-accent to-qace-primary transition-all" style={{ width: `${safeValue}%` }} />
      </div>
      {hint ? <p className="text-xs text-qace-muted/80">{hint}</p> : null}
    </div>
  );
}
