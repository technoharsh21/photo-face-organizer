export const metadata = {
  title: "Unknown Faces Management | Photo Face Organizer Docs",
  description: "Review unmatched face clusters and convert them into new profiles.",
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
          How unmatched face thumbnails are stored and converted into new profiles.
        </p>
      </div>

      <div className="space-y-6 text-sm leading-relaxed">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">1. Face Crop Storage</h2>
        <p>
          When a face in a photo does not match any selected profile above the confidence threshold, its cropped thumbnail image and 128-dimensional facial embedding are saved into your local Unknown Faces store.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">2. Grouping &amp; Clustering Similar Faces</h2>
        <p>
          On the <strong>❓ Unknown Faces</strong> page in the desktop app, click <strong>🔄 Group Similar Faces</strong>. The engine clusters similar unknown faces together into groups representing recurring unrecognized people.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">3. Converting Clusters to Profiles</h2>
        <p>
          Select an unknown group and click <strong>⭐ Convert Group to Profile</strong>. Enter a profile name (e.g. &quot;Uncle Dave&quot;). The app automatically creates a new profile and converts the crop images into reference photos!
        </p>
      </div>
    </div>
  );
}
