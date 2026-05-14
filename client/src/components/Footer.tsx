"use client";

import Link from "next/link";
import BrandLogo from "@/components/BrandLogo";

type FooterProps = {
  variant?: "app" | "marketing";
};

const productLinks = [
  { label: "Setup", href: "/setup" },
  { label: "Live Session", href: "/session/lobby" },
  { label: "Practice", href: "/practice" },
  { label: "Reports", href: "/reports" },
];

const supportLinks = [
  { label: "About", href: "/about" },
  { label: "Help Center", href: "/help" },
  { label: "Settings", href: "/settings" },
];

export default function Footer({ variant = "app" }: FooterProps) {
  const year = new Date().getFullYear();

  return (
    <footer
      className={`relative z-10 mt-16 mb-6 rounded-2xl border border-white/10 bg-black/20 backdrop-blur-md ${
        variant === "marketing" ? "" : "mx-auto w-full max-w-[92rem]"
      }`}
    >
      <div
        className={`mx-auto w-full px-4 py-8 sm:px-6 md:px-8 ${
          variant === "marketing" ? "max-w-6xl" : "max-w-[92rem]"
        }`}
      >
        <div className="grid gap-8 md:grid-cols-3 md:gap-6">
          <div>
            <Link href="/" className="inline-flex items-center gap-2">
              <BrandLogo className="h-7 w-auto text-white" />
              <span className="text-lg font-semibold tracking-tight text-white">
                Q&A<span className="text-sky-400">ce</span>
              </span>
            </Link>
            <p className="mt-3 max-w-xs text-sm text-qace-muted">
              AI-powered interview preparation with multimodal feedback,
              progress tracking, and realistic mock sessions.
            </p>
          </div>

          <div>
            <h4 className="text-xs font-semibold uppercase tracking-[0.18em] text-white/70">
              Product
            </h4>
            <ul className="mt-3 space-y-2 text-sm text-qace-muted">
              {productLinks.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="transition hover:text-white"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-semibold uppercase tracking-[0.18em] text-white/70">
              Support
            </h4>
            <ul className="mt-3 space-y-2 text-sm text-qace-muted">
              {supportLinks.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="transition hover:text-white"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="mt-8 flex flex-col items-center justify-between gap-3 border-t border-white/10 pt-5 text-xs text-qace-muted sm:flex-row">
          <p>
            &copy; {year} Q&amp;Ace. All rights reserved.
          </p>
          <p className="text-center sm:text-right">
            Built as a Final Year Project &middot;{" "}
            <span className="text-white/70">Q&amp;Ace Team</span>
          </p>
        </div>
      </div>
    </footer>
  );
}
