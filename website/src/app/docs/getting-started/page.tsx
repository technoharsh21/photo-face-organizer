import Link from "next/link";
import { ArrowRight, CheckCircle2 } from "lucide-react";

export const metadata = {
  title: "Getting Started Guide | Photo Face Organizer Docs",
  description: "Learn the core workflow, profile setup, and photo scanning in Photo Face Organizer.",
};

export default function GettingStartedPage() {
  return (
    <div className="space-y-8 text-slate-700 dark:text-slate-300">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
        <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
          Overview
        </span>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          Getting Started Guide
        </h1>
        <p className="text-sm text-slate-500">
          A step-by-step introduction to setting up profiles and organizing your photo collection.
        </p>
      </div>

      <div className="space-y-6 text-sm leading-relaxed">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">1. Basic Workflow</h2>
        <p>
          Photo Face Organizer is designed around a simple, non-destructive 5-step process:
        </p>

        <ol className="list-decimal list-inside space-y-2 font-medium text-slate-800 dark:text-slate-200">
          <li><strong>Create Person Profiles</strong> (Add reference photos of target people).</li>
          <li><strong>Select Source Folders</strong> (Choose local image directories to analyze).</li>
          <li><strong>Select Target Output Location</strong> (Specify where organized photo copies will be placed).</li>
          <li><strong>Launch the Scan</strong> (The local AI engine matches faces against profiles).</li>
          <li><strong>Review Results &amp; Audit Summary</strong> (Inspect matched person folders and File Reconciliation Summary).</li>
        </ol>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white pt-4">2. Non-Destructive Copy Safety</h2>
        <p>
          Photo Face Organizer <strong>never modifies, moves, renames, or deletes your original source photos</strong>. All matching photos are safely copied into your chosen target output directory inside clean subfolders named after each person.
        </p>

        <div className="p-4 rounded-xl bg-brand-50 dark:bg-brand-950/50 border border-brand-200 dark:border-brand-900 text-brand-900 dark:text-brand-200 text-xs">
          <strong>File Collision Safety:</strong> If a file with the same name already exists in your output folder, the application automatically appends a number suffix (e.g. <code>photo_1.jpg</code>) to ensure no files are overwritten.
        </div>
      </div>

      <div className="pt-6 border-t border-slate-200 dark:border-slate-800 flex justify-between">
        <Link href="/docs/installation" className="text-xs font-semibold text-brand-600 hover:underline">
          &larr; Installation Overview
        </Link>
        <Link href="/docs/profiles" className="text-xs font-semibold text-brand-600 hover:underline flex items-center gap-1">
          <span>Creating Profiles</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  );
}
