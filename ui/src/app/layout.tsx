import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Billing Agent",
  description: "AI-powered electricity bill explanation — powered by DEH",
  icons: {
    icon: "/bot-picture.png",
    apple: "/bot-picture.png",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
