import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Billing RAG Agent",
  description: "AI-powered electricity bill explanation — Vision → Match → RAG",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen">
        <header className="bg-white border-b border-gray-200 shadow-sm">
          <div className="max-w-3xl mx-auto px-4 py-4 flex items-center gap-3">
            <span className="text-2xl">⚡</span>
            <div>
              <h1 className="text-lg font-bold text-gray-900 leading-none">Billing RAG Agent</h1>
              <p className="text-xs text-gray-500 mt-0.5">Vision · Match · Retrieve · Answer</p>
            </div>
          </div>
        </header>
        <main className="max-w-3xl mx-auto px-4 py-8">{children}</main>
      </body>
    </html>
  );
}

