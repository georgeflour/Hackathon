import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ΔΕΗ Smart Bill Assistant",
  description: "AI-powered electricity bill explanation — powered by ΔΕΗ",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="el">
      <body>{children}</body>
    </html>
  );
}
