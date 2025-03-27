import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import "./fonts.css"; // Import custom fonts

// Import Inter font
const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Hanzo Dashboard",
  description: "Hanzo AI Platform Dashboard",
  icons: {
    icon: "/favicon.ico", // Use local favicon
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
