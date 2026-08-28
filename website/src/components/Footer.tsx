import Link from "next/link";
import Image from "next/image";
import { ShieldCheck, Github } from "lucide-react";

export function Footer() {
  const repoUrl = process.env.NEXT_PUBLIC_GITHUB_REPO
    ? `https://github.com/${process.env.NEXT_PUBLIC_GITHUB_REPO}`
    : "https://github.com/technoharsh21/photo-face-organizer";

  return (
    <footer className="border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 text-slate-600 dark:text-slate-400 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand Col */}
          <div className="space-y-4 md:col-span-1">
            <Link href="/" className="flex items-center gap-2 font-bold text-slate-900 dark:text-white">
              <div className="p-1 rounded-lg bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex items-center justify-center">
                <Image
                  src="/logo.png"
                  alt="Photo Face Organizer Logo"
                  width={24}
                  height={24}
                  className="w-6 h-6 object-contain"
                />
              </div>
              <span>Photo Face Organizer</span>
            </Link>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              Open-source, 100% local-first photo face recognition and automated folder routing. Your privacy is fully preserved.
            </p>
            <div className="flex items-center gap-2 text-xs text-emerald-600 dark:text-emerald-400 font-medium">
              <ShieldCheck className="w-4 h-4" />
              <span>Zero Cloud Uploads</span>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-900 dark:text-slate-200 mb-3">
              Navigation
            </h3>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/" className="hover:text-slate-900 dark:hover:text-slate-200 transition-colors">
                  Home
                </Link>
              </li>
              <li>
                <Link href="/download" className="hover:text-slate-900 dark:hover:text-slate-200 transition-colors">
                  Download
                </Link>
              </li>
              <li>
                <Link href="/releases" className="hover:text-slate-900 dark:hover:text-slate-200 transition-colors">
                  Release History
                </Link>
              </li>
              <li>
                <Link href="/faq" className="hover:text-slate-900 dark:hover:text-slate-200 transition-colors">
                  FAQ
                </Link>
              </li>
            </ul>
          </div>

          {/* Documentation */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-900 dark:text-slate-200 mb-3">
              Documentation
            </h3>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/docs/getting-started" className="hover:text-slate-900 dark:hover:text-slate-200 transition-colors">
                  Getting Started
                </Link>
              </li>
              <li>
                <Link href="/docs/installation/linux" className="hover:text-slate-900 dark:hover:text-slate-200 transition-colors">
                  Linux Setup (.deb)
                </Link>
              </li>
              <li>
                <Link href="/docs/installation/windows" className="hover:text-slate-900 dark:hover:text-slate-200 transition-colors">
                  Windows Setup (.exe)
                </Link>
              </li>
              <li>
                <Link href="/docs/group-photos" className="hover:text-slate-900 dark:hover:text-slate-200 transition-colors">
                  Group Profile Rules
                </Link>
              </li>
            </ul>
          </div>

          {/* Legal & Open Source */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-900 dark:text-slate-200 mb-3">
              Open Source
            </h3>
            <ul className="space-y-2 text-sm">
              <li>
                <a
                  href={repoUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 hover:text-slate-900 dark:hover:text-slate-200 transition-colors"
                >
                  <Github className="w-4 h-4" />
                  <span>GitHub Repository</span>
                </a>
              </li>
              <li>
                <Link href="/privacy" className="hover:text-slate-900 dark:hover:text-slate-200 transition-colors">
                  Privacy Policy
                </Link>
              </li>
              <li>
                <Link href="/contact" className="hover:text-slate-900 dark:hover:text-slate-200 transition-colors">
                  Contact Us
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-8 pt-8 border-t border-slate-200 dark:border-slate-800 text-xs text-slate-400 text-center md:text-left flex flex-col md:flex-row justify-between items-center gap-4">
          <p>© {new Date().getFullYear()} Photo Face Organizer. MIT Licensed Open Source Software.</p>
          <p className="text-slate-400 dark:text-slate-500">
            Local-first AI face recognition desktop application.
          </p>
        </div>
      </div>
    </footer>
  );
}
