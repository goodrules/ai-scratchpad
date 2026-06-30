import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Software Bug Assistant",
  description: "AI-powered software bug triage and analysis",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full overflow-hidden">{children}</body>
    </html>
  );
}
