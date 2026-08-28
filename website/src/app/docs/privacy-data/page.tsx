export const metadata = {
  title: "Privacy & File Safety | Photo Face Organizer Docs",
  description: "Learn about our local-first data storage and non-destructive file routing safety.",
};

export default function PrivacyDataDocPage() {
  return (
    <div className="space-y-8 text-slate-700 dark:text-slate-300">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
        <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
          Architecture &rsaquo; Privacy
        </span>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          Privacy Architecture &amp; File Safety
        </h1>
        <p className="text-sm text-slate-500">
          How local data storage and copy-only safeguards keep your photos private and secure.
        </p>
      </div>

      <div className="space-y-6 text-sm leading-relaxed">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">1. Local-First Processing Architecture</h2>
        <p>
          Photo Face Organizer is built on a strict <strong>local-first philosophy</strong>. All image decoding, EXIF orientation processing, face embedding calculations, and profile storage occur entirely on your local file system.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">2. Original File Integrity</h2>
        <p>
          Your source photos are treated as read-only assets. The application <strong>never modifies, moves, deletes, or alters your original photos</strong>. All organized results are saved as clean copies in your specified output directory.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">3. Application Storage Directories</h2>
        <p>
          Local application data (profiles, reference crops, and scan logs) is stored in standard local user data directories:
        </p>

        <ul className="list-disc list-inside space-y-1 font-mono text-xs text-slate-600 dark:text-slate-400">
          <li><strong>Linux:</strong> <code>~/.local/share/PhotoFaceOrganizer/</code></li>
          <li><strong>Windows:</strong> <code>C:\Users\&lt;User&gt;\AppData\Local\PhotoFaceOrganizer\</code></li>
          <li><strong>macOS:</strong> <code>~/Library/Application Support/PhotoFaceOrganizer/</code></li>
        </ul>
      </div>
    </div>
  );
}
