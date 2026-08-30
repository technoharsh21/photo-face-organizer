export const metadata = {
  title: "Duplicate Photos Finder | Photo Face Organizer Docs",
  description: "High-speed cryptographic SHA-256 duplicate photo detection and non-destructive cleanup.",
};

export default function DuplicatesDocPage() {
  return (
    <div className="space-y-8 text-slate-700 dark:text-slate-300">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
        <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
          Usage Guide &rsaquo; Duplicates
        </span>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          Duplicate Photos Finder &amp; Safe Cleanup
        </h1>
        <p className="text-sm text-slate-500">
          How to detect 100% identical duplicate photos across deep directory structures with zero false positives.
        </p>
      </div>

      <div className="space-y-6 text-sm leading-relaxed">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          1. Why Cryptographic Detection?
        </h2>
        <p>
          Photo libraries often accumulate exact duplicate photos due to multiple backups, WhatsApp syncs, camera SD card dumps, and nested folders. Photo Face Organizer uses <strong>SHA-256 Cryptographic Hashing</strong> to guarantee 100% byte-for-byte identification (0.00% false duplicate risk).
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          2. The 3-Tier Ultra-Fast CPU Pipeline
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1.5">
            <span className="text-xs font-mono font-bold text-brand-600 dark:text-brand-400">TIER 1</span>
            <h4 className="font-bold text-slate-900 dark:text-white text-sm">Instant Size Filter</h4>
            <p className="text-xs text-slate-500">Inspects file metadata. Files with unique byte sizes are instantly discarded with 0 ms disk read overhead.</p>
          </div>
          <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1.5">
            <span className="text-xs font-mono font-bold text-purple-600 dark:text-purple-400">TIER 2</span>
            <h4 className="font-bold text-slate-900 dark:text-white text-sm">Hardware SHA-256</h4>
            <p className="text-xs text-slate-500">Candidate files sharing identical byte sizes are hashed using CPU Intel SHA / AES-NI extensions at multi-GB/s speed.</p>
          </div>
          <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1.5">
            <span className="text-xs font-mono font-bold text-emerald-600 dark:text-emerald-400">TIER 3</span>
            <h4 className="font-bold text-slate-900 dark:text-white text-sm">Smart Grouping</h4>
            <p className="text-xs text-slate-500">Duplicates are grouped side-by-side with timestamps, file paths, and automated selection recommendations.</p>
          </div>
        </div>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          3. Smart Auto-Selection Rules
        </h2>
        <p>
          Managing hundreds of duplicates manually is tedious. The Duplicate Finder includes smart 1-click rules:
        </p>
        <ul className="list-disc list-inside space-y-1.5 pl-2 text-slate-600 dark:text-slate-400">
          <li><strong>Keep Oldest:</strong> Preserves the earliest created original copy and marks newer redundant copies for cleanup.</li>
          <li><strong>Keep Newest:</strong> Preserves the most recently modified copy.</li>
          <li><strong>Keep Shortest Path:</strong> Preserves copies organized in shallow, clean folders (e.g. <code>Photos/2026/img.jpg</code>) while marking deeply nested copies (e.g. <code>Backup/Old/Temp/img.jpg</code>).</li>
        </ul>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          4. Non-Destructive Safe Cleanup Modes
        </h2>
        <p>
          Before removing files, you can choose the safety level:
        </p>
        <ul className="list-disc list-inside space-y-1.5 pl-2 text-slate-600 dark:text-slate-400">
          <li><strong>Recycle Bin / Trash (Default):</strong> Moves duplicate files to your operating system&apos;s Recycle Bin / Trash for easy recovery if needed.</li>
          <li><strong>Quarantine Folder:</strong> Moves duplicates into a timestamped local app quarantine folder.</li>
          <li><strong>Permanent Delete:</strong> Deletes duplicate files directly from disk after user confirmation.</li>
        </ul>
      </div>
    </div>
  );
}
