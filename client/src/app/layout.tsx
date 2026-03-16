import type { Metadata } from "next";
import { Manrope, Sora } from "next/font/google";
import MagneticHoverProvider from "@/components/MagneticHoverProvider";
import "./globals.css";

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-body",
});

const sora = Sora({
  subsets: ["latin"],
  variable: "--font-heading",
});

export const metadata: Metadata = {
  title: "Q&Ace | AI Interview Coach",
  description:
    "Real-time interview preparation with AI coaching, multimodal feedback, and performance analytics.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body
        className={`${manrope.variable} ${sora.variable} min-h-screen bg-qace-dark text-qace-text antialiased`}
      >
        <MagneticHoverProvider />
        {children}
      </body>
    </html>
  );
}
