import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";

const inter = Inter({ subsets: ["latin"] });

const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://photo-face-organizer.vercel.app";

export const metadata: Metadata = {
  metadataBase: new URL(baseUrl),
  title: {
    default: "Photo Face Organizer | 100% Local AI Photo Sorter & Face Recognition",
    template: "%s | Photo Face Organizer",
  },
  description:
    "Open-source desktop application that automatically detects, recognizes, and organizes photos into person and group folders. 100% local-first, zero cloud uploads, original photos never modified.",
  keywords: [
    "photo organizer",
    "face recognition",
    "local AI photo sorter",
    "group photo matching",
    "privacy focused photo manager",
    "open source photo sorter",
    "desktop application",
  ],
  authors: [{ name: "Photo Face Organizer Team" }],
  icons: {
    icon: "/favicon.ico",
    shortcut: "/favicon.ico",
    apple: "/icon.png",
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: baseUrl,
    title: "Photo Face Organizer | Local AI Photo Sorter",
    description:
      "Automatically recognize people and route photos into person folders. 100% local processing, zero cloud uploads.",
    siteName: "Photo Face Organizer",
    images: [
      {
        url: "/logo.png",
        width: 512,
        height: 512,
        alt: "Photo Face Organizer Logo",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Photo Face Organizer | Local AI Photo Sorter",
    description:
      "Automatically recognize people and route photos into person folders. 100% local processing, zero cloud uploads.",
    images: ["/logo.png"],
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <div className="flex flex-col min-h-screen">
            <Navbar />
            <main className="flex-grow">{children}</main>
            <Footer />
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
