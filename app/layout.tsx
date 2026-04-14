import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mojo — Agentic Trading OS",
  description: "Speak a strategy. Agent runs it 24/7.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
