import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Hanzo Dashboard",
  description: "Hanzo AI Platform Dashboard",
  icons: {
    icon: "https://api.hanzo.ai/favicon.ico", // Use the favicon from api.hanzo.ai
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-black text-white dark`}>{children}</body>
    </html>
  );
}
