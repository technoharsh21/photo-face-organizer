import { MetadataRoute } from "next";
import { RELEASES_DATA } from "@/data/releases";
import { DOCS_NAV } from "@/data/docs";

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://photo-face-organizer.vercel.app";

  const staticPages = [
    "",
    "/download",
    "/releases",
    "/docs",
    "/faq",
    "/contact",
    "/privacy",
  ].map((route) => ({
    url: `${baseUrl}${route}`,
    lastModified: new Date(),
    changeFrequency: "weekly" as const,
    priority: route === "" ? 1.0 : 0.8,
  }));

  const releasePages = RELEASES_DATA.map((r) => ({
    url: `${baseUrl}/releases/${r.version}`,
    lastModified: new Date(r.releaseDate),
    changeFrequency: "monthly" as const,
    priority: 0.7,
  }));

  const docsPages = DOCS_NAV.map((d) => ({
    url: `${baseUrl}${d.href}`,
    lastModified: new Date(),
    changeFrequency: "monthly" as const,
    priority: 0.7,
  }));

  return [...staticPages, ...releasePages, ...docsPages];
}
