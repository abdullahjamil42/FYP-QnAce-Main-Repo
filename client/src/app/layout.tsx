import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Q&Ace — AI Interview Prep",
  description:
    "Real-time AI interview preparation with speech analysis and avatar feedback",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-qace-dark text-qace-text antialiased">
        {children}
      </body>
    </html>
  );
}
