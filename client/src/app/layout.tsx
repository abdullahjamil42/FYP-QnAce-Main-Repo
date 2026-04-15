import type { Metadata } from "next";
import { Manrope, Sora } from "next/font/google";
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
      <head>
        <script
          type="importmap"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              imports: {
                three: "https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js/+esm",
                "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.180.0/examples/jsm/",
                talkinghead: "https://cdn.jsdelivr.net/gh/met4citizen/TalkingHead@1.7/modules/talkinghead.mjs",
              },
            }),
          }}
        />
      </head>
      <body
        className={`${manrope.variable} ${sora.variable} min-h-screen bg-qace-dark text-qace-text antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
