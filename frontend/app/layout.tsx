import type { Metadata } from "next";
import "./globals.css";
import { Footer } from "./components/Footer";

export const metadata: Metadata = {
  title: "YGO Meta Check",
  description: "Search any Yu-Gi-Oh! card to see if it has recent tournament meta relevance.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        {children}
        <Footer />
      </body>
    </html>
  );
}
