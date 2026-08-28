# Photo Face Organizer - Official Website

Production-ready, local-first Next.js 14 website for **Photo Face Organizer** desktop application.

Built with Next.js (App Router), TypeScript, Tailwind CSS, Lucide React, Zod, and Nodemailer.

---

## 🚀 Features

- **Smart OS Detection**: Automatically recommends the appropriate download format (Linux `.deb` / ZIP, Windows `.exe`, macOS `.dmg` / `pip install`) with a manual fallback selector.
- **Centralized Release Architecture**: Typed release data model (`src/data/releases.ts`) driving Home, Download, Releases, and Documentation pages.
- **Full Release History**: Detailed version release notes, highlights, download assets, and SHA256 checksum verification.
- **Comprehensive Documentation**: Complete guides for Linux (`.deb`, `pipx`), Windows (`.exe` Inno Setup), macOS, Profile Creation, Compulsory Group Matching, Unknown Faces, GPU Acceleration, and Privacy Architecture.
- **Contact Us Form**: Server-side Nodemailer email handler with Zod validation, sliding-window IP rate limiting, honeypot spam protection, and safe error handling.
- **Privacy & File Safety**: Complete explanation of local-first photo processing and original file copy protection.
- **SEO & Accessibility**: Dynamic `sitemap.xml`, `robots.txt`, OpenGraph metadata, light/dark mode with system preference detection, and keyboard navigation.

---

## 🛠️ Local Development & Setup

```bash
# 1. Install dependencies
npm install

# 2. Run local development server
npm run dev

# 3. Run ESLint checks
npm run lint

# 4. Run automated test suite
npm test

# 5. Build for production
npm run build
```

---

## 🔑 Environment Variables Configuration

Copy `.env.example` to `.env.local`:

```bash
cp .env.example .env.local
```

### Environment Variables Matrix:

| Variable | Description | Example |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_SITE_URL` | Canonical website domain (used for sitemap, robots, OpenGraph) | `https://photo-face-organizer.vercel.app` |
| `NEXT_PUBLIC_GITHUB_REPO` | GitHub repository path (`username/repo`) | `technoharsh21/photo-face-organizer` |
| `SMTP_HOST` | SMTP server host for Contact Us emails | `smtp.example.com` |
| `SMTP_PORT` | SMTP port (587 for TLS, 465 for SSL) | `587` |
| `SMTP_USER` | SMTP authentication username | `contact@example.com` |
| `SMTP_PASSWORD` | SMTP authentication password / app secret | `your-secret-password` |
| `CONTACT_EMAIL` | Destination email address to receive contact form submissions | `support@technoharsh.com` |

*Note: If SMTP environment variables are unconfigured, the Contact form gracefully displays a user-friendly message without exposing stack traces or server details.*

---

## ☁️ Vercel Deployment Guide

1. Push the `website` directory to your GitHub repository.
2. Go to [Vercel Dashboard](https://vercel.com/new) and select **Import Project**.
3. Select your repository and set the **Root Directory** to `website`.
4. Add your Production Environment Variables (`NEXT_PUBLIC_SITE_URL`, `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `CONTACT_EMAIL`).
5. Click **Deploy**. Vercel will automatically build and publish your site!
