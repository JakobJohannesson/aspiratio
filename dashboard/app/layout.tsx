import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Aspiratio - Coverage Dashboard",
  description: "Annual report download coverage for Nordic companies",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
