import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Daily Berlin Jobs",
  description: "Fresh engineering jobs in Berlin, updated daily.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
