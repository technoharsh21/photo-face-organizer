import { ShieldCheck, HardDrive, Lock } from "lucide-react";

export const metadata = {
  title: "Privacy Policy | Photo Face Organizer",
  description: "Learn about the local-first privacy model of Photo Face Organizer and our website data protection standards.",
};

export default function PrivacyPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-10 text-slate-700 dark:text-slate-300">
      {/* Header */}
      <div className="space-y-4 border-b border-slate-200 dark:border-slate-800 pb-6">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-900 text-emerald-700 dark:text-emerald-300 text-xs font-semibold">
          <ShieldCheck className="w-4 h-4" />
          <span>Local-First Privacy Architecture</span>
        </div>
        <h1 className="text-4xl font-extrabold text-slate-900 dark:text-white">
          Privacy Policy
        </h1>
        <p className="text-slate-500 text-sm">
          Last Updated: August 28, 2026
        </p>
      </div>

      <div className="space-y-8 text-sm leading-relaxed">
        {/* Section 1: Desktop Application Privacy */}
        <section className="p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600">
              <HardDrive className="w-5 h-5" />
            </div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">
              1. Desktop Application Privacy
            </h2>
          </div>

          <p>
            <strong>Photo Face Organizer</strong> is engineered from the ground up as a 100% local-first desktop application.
          </p>

          <ul className="list-disc list-inside space-y-2 text-slate-600 dark:text-slate-300">
            <li>
              <strong>Zero Cloud Uploads:</strong> All face detection, face recognition encoding, profile storage, and photo folder routing happen entirely on your computer&apos;s local hardware. Your photos and facial embeddings are never uploaded to any cloud server or remote service.
            </li>
            <li>
              <strong>Original File Safety:</strong> Original photos are never moved, deleted, renamed, or modified. The desktop application operates strictly in non-destructive copy mode.
            </li>
            <li>
              <strong>Local Data Storage:</strong> Profiles, reference photo crops, and scan logs are stored in standard OS application directories on your computer (e.g., <code>~/.local/share/PhotoFaceOrganizer</code> on Linux). You have complete ownership and control over these files.
            </li>
          </ul>
        </section>

        {/* Section 2: Website Privacy */}
        <section className="p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-brand-100 dark:bg-brand-950/60 text-brand-600">
              <Lock className="w-5 h-5" />
            </div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">
              2. Website Data &amp; Contact Submissions
            </h2>
          </div>

          <p>
            When you visit our website or use the Contact Us form:
          </p>

          <ul className="list-disc list-inside space-y-2 text-slate-600 dark:text-slate-300">
            <li>
              <strong>Contact Form Data:</strong> If you fill out the Contact Us form, we collect your name, email address, subject, and message solely to respond to your inquiry. We do not sell or share your contact details.
            </li>
            <li>
              <strong>No Tracking Cookies:</strong> This website does not use invasive third-party tracking cookies or advertising pixels.
            </li>
            <li>
              <strong>Server Logs:</strong> Standard web hosting infrastructure logs IP addresses and user agents temporarily for security and rate limiting purposes.
            </li>
          </ul>
        </section>

        {/* Section 3: Contact Info */}
        <section className="p-6 rounded-2xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-2">
          <h3 className="font-bold text-slate-900 dark:text-white">Privacy Questions &amp; Support</h3>
          <p className="text-xs text-slate-600 dark:text-slate-400">
            If you have any questions regarding privacy, open-source code security, or data handling, please contact us via our Contact Us page or open an issue on our GitHub repository.
          </p>
        </section>
      </div>
    </div>
  );
}
