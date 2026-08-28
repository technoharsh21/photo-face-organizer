import Link from "next/link";
import { DOCS_NAV } from "@/data/docs";
import { BookOpen, ArrowRight } from "lucide-react";

export const metadata = {
  title: "Documentation | Photo Face Organizer",
  description: "Comprehensive documentation, user guides, and installation instructions for Photo Face Organizer.",
};

export default function DocsIndexPage() {
  return (
    <div className="space-y-8">
      <div className="space-y-3 border-b border-slate-200 dark:border-slate-800 pb-6">
        <div className="inline-flex items-center gap-2 text-xs font-semibold text-brand-600 dark:text-brand-400">
          <BookOpen className="w-4 h-4" />
          <span>DOCUMENTATION PORTAL</span>
        </div>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          Photo Face Organizer Documentation
        </h1>
        <p className="text-slate-600 dark:text-slate-400 text-base">
          Learn how to install, configure, and get the most out of Photo Face Organizer desktop application.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {DOCS_NAV.map((doc) => (
          <Link
            key={doc.href}
            href={doc.href}
            className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-brand-500 dark:hover:border-brand-500 transition-colors space-y-2 group"
          >
            <div className="text-xs font-semibold text-brand-600 dark:text-brand-400">
              {doc.category}
            </div>
            <h3 className="text-base font-bold text-slate-900 dark:text-white group-hover:text-brand-600 dark:group-hover:text-brand-400 flex items-center justify-between">
              <span>{doc.title}</span>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:translate-x-1 transition-transform" />
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {doc.description}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}
