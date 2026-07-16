import type { Metadata } from "next";
import { Analytics } from "@vercel/analytics/next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Daily Berlin Jobs",
  description: "Fresh engineering jobs in Berlin, updated daily.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        {children}
        <Analytics />
      </body>
    </html>
  );
}
