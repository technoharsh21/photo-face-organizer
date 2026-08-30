export const metadata = {
  title: "Solo Photo Scanning | Photo Face Organizer Docs",
  description: "Create pure individual photo albums with 360° profile-angle face detection and stranger exclusion.",
};

export default function SoloScanDocPage() {
  return (
    <div className="space-y-8 text-slate-700 dark:text-slate-300">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
        <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
          Usage Guide &rsaquo; Solo Scanning
        </span>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          Solo Photo Scanning &amp; Pure Album Creation
        </h1>
        <p className="text-sm text-slate-500">
          How to isolate true solo portraits and exclusive couple photos with zero outsider contamination.
        </p>
      </div>

      <div className="space-y-6 text-sm leading-relaxed">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          1. What is Solo Photo Scanning?
        </h2>
        <p>
          Standard scans copy any photo containing a person into their folder—even if it is a crowded group photo with 10 other people. <strong>Solo Photo Scanning</strong> enforces a strict purity rule: <strong>a photo is only copied into a person&apos;s folder if they are the ONLY person present in that photo.</strong>
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          2. Multi-Angle &amp; 90&deg; Side Profile Face Detection
        </h2>
        <p>
          Real-world photos often feature a person facing forward while a companion or bystander is turned sideways (profile view) or looking away. Older facial detectors miss side-facing heads because they only look for two visible eyes and a frontal nose.
        </p>
        <p>
          Photo Face Organizer uses deep <strong>SCRFD 360&deg; Detection</strong> tuned at a sensitive base threshold of <code>det_thresh = 0.35</code>:
        </p>
        <ul className="list-disc list-inside space-y-1.5 pl-2 text-slate-600 dark:text-slate-400">
          <li><strong>90&deg; Side-Profile Faces:</strong> Detects jawlines, side-eye, and ear profiles.</li>
          <li><strong>Tilted &amp; Looking-Away Heads:</strong> Detects heads turned up to 90&deg; yaw and pitch.</li>
          <li><strong>5-Point Landmark Validation:</strong> Checks anatomical eye-to-nose geometry to ensure clothing prints or wallpaper patterns are never mistaken for human faces.</li>
        </ul>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          3. Deep Secondary Background Exclusion Verification
        </h2>
        <p>
          Whenever initial AI detection returns exactly 1 face on a high-resolution photo, the engine automatically triggers a <strong>secondary high-sensitivity verification pass (<code>det_thresh = 0.28</code>)</strong>.
        </p>
        <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-2 text-xs">
          <p className="font-semibold text-slate-800 dark:text-slate-200">The 2-Stage Verification Workflow:</p>
          <p>&bull; <strong>Stage 1:</strong> Initial detector spots 1 front-facing subject.</p>
          <p>&bull; <strong>Stage 2 (Deep Exclusion Scan):</strong> Engine scans the background at 0.28 threshold for distant bystanders, turned heads, or shadowed companions.</p>
          <p>&bull; <strong>Result:</strong> If any second face is discovered anywhere in the photo, the total count becomes &ge; 2, and the photo is <strong>instantly excluded</strong> from the Solo folder as a group photo.</p>
        </div>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          4. Exclusive Couple &amp; Duo Group Solo Scanning
        </h2>
        <p>
          If you create an <strong>Exclusive Group Profile for 2 people</strong> (e.g., <em>&quot;Harsh &amp; Arya&quot;</em>):
        </p>
        <ul className="list-disc list-inside space-y-1.5 pl-2 text-slate-600 dark:text-slate-400">
          <li><strong>Photo with Harsh + Arya (Exactly 2 faces):</strong> &rarr; <span className="text-emerald-600 dark:text-emerald-400 font-semibold">MATCHED</span> and copied to the couple album.</li>
          <li><strong>Photo with Harsh + Arya + 1 Friend (3 faces):</strong> &rarr; <span className="text-rose-600 dark:text-rose-400 font-semibold">REJECTED</span> (Outsider present).</li>
          <li><strong>Photo with Harsh + Stranger (2 faces):</strong> &rarr; <span className="text-rose-600 dark:text-rose-400 font-semibold">REJECTED</span> (Arya missing).</li>
          <li><strong>Photo with Only Harsh (1 face):</strong> &rarr; Routed to Harsh&apos;s individual solo folder, not the couple folder.</li>
        </ul>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          5. Intelligent Photobomber &amp; Crowd Framing Options
        </h2>
        <p>
          When photographing in public locations (beaches, tourist landmarks, city streets), tiny 10-pixel bystanders may appear hundreds of meters away in the background.
        </p>
        <p>
          The scanner allows selecting between <strong>Strict Studio Mode</strong> (zero tolerance for any face in the background) and <strong>Dominant Subject Mode</strong> (recognizes solo portraits where the subject occupies &ge; 90% of facial area and background faces are tiny distant bystanders).
        </p>
      </div>
    </div>
  );
}
