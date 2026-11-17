import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BuildX Challenge 05 | Waste Collection Planner",
  description:
    "Capacity-aware waste collection routing for a simulated Colombo service area.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
