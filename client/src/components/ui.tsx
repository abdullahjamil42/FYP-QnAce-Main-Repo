import type { ReactNode } from "react";

type CardProps = {
  children: ReactNode;
  className?: string;
};

export function GlassCard({ children, className = "" }: CardProps) {
  return (
    <article className={`apple-glass rounded-3xl p-6 transition-all duration-300 ${className}`}>
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
      ? "bg-green-500/20 text-green-400 border border-green-500/30"
      : tone === "warning"
        ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
        : "bg-white/10 text-slate-200 border border-white/20";

  return <span className={`rounded-full px-3 py-1 text-xs font-semibold tracking-wide backdrop-blur-md ${toneClass}`}>{children}</span>;
}

type ProgressProps = {
  label: string;
  value: number;
  hint?: string;
};

export function ProgressRow({ label, value, hint }: ProgressProps) {
  const safeValue = Math.max(0, Math.min(100, value));

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-[var(--muted)] font-medium tracking-tight">{label}</span>
        <span className="font-semibold text-white">{safeValue.toFixed(0)}</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
        <div 
          className="h-full rounded-full transition-all duration-1000 ease-out" 
          style={{ width: `${safeValue}%`, background: 'var(--accent-hover)', boxShadow: '0 0 10px var(--accent-hover)' }} 
        />
      </div>
      {hint ? <p className="text-xs text-[var(--muted)] opacity-80 pt-1">{hint}</p> : null}
    </div>
  );
}
