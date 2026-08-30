export const metadata = {
  title: "Unknown Faces Management | Photo Face Organizer Docs",
  description: "Review unmatched face clusters and convert verified 4/5-star crops into new profiles.",
};

export default function UnknownFacesDocPage() {
  return (
    <div className="space-y-8 text-slate-700 dark:text-slate-300">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
        <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
          Usage Guide &rsaquo; Unknown Faces
        </span>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          Unknown Faces &amp; Cluster Conversion
        </h1>
        <p className="text-sm text-slate-500">
          How unmatched face thumbnails are stored, auto-clustered, and converted into verified person profiles.
        </p>
      </div>

      <div className="space-y-6 text-sm leading-relaxed">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">1. High-Quality Face Crop Storage</h2>
        <p>
          When a face in a photo does not match any selected profile above the confidence threshold, its cropped thumbnail image and 512-dimensional ArcFace embedding are evaluated for quality:
        </p>
        <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs space-y-1">
          <p><strong>⭐ Quality Gate:</strong> Only faces scoring <strong>4 or 5 stars</strong> (sharp edge contours, high resolution, healthy lighting) are saved. Blurry or distant bystander artifacts are automatically discarded.</p>
        </div>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">2. High-Precision Face Clustering</h2>
        <p>
          On the <strong>❓ Unknown Faces</strong> page, the engine automatically clusters similar unknown faces (&ge; 80% similarity matrix) into distinct person groups representing recurring unrecognized individuals in your library.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">3. Converting Clusters to Profiles</h2>
        <p>
          Select an unknown group and click <strong>⭐ Convert Group to Profile</strong>. Enter a profile name (e.g. &quot;Uncle Dave&quot;). The app automatically creates a new profile and converts the verified 4/5-star crop images into reference photos!
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">4. Auto-Purging &amp; Privacy</h2>
        <p>
          If source photos are moved or deleted on your computer, the app automatically purges orphaned unknown face records to conserve disk space. You can also click <strong>Purge All</strong> to wipe all unknown faces instantly.
        </p>
      </div>
    </div>
  );
}
