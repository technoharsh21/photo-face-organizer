export const metadata = {
  title: "Creating Profiles & Reference Photos | Photo Face Organizer Docs",
  description: "Learn how to create individual and group profiles, add high-quality reference images, and clean outliers.",
};

export default function ProfilesDocPage() {
  return (
    <div className="space-y-8 text-slate-700 dark:text-slate-300">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
        <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
          Usage Guide &rsaquo; Profiles
        </span>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          Creating People Profiles &amp; Reference Management
        </h1>
        <p className="text-sm text-slate-500">
          How to build person profiles, upload 4/5-star reference photos, and maintain clean identity datasets.
        </p>
      </div>

      <div className="space-y-6 text-sm leading-relaxed">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">1. Creating an Individual Profile</h2>
        <p>
          In the <strong>People Management</strong> section, click <strong>➕ Create Profile</strong>. Enter a person&apos;s name (e.g., &quot;Harsh&quot; or &quot;Alice&quot;) and select <strong>Individual Person Profile</strong>.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">2. Adding 4 &amp; 5-Star Reference Photos</h2>
        <p>
          Click <strong>📷 Add Reference Photo</strong> to upload clear images of the person. You can upload multiple reference photos from different angles (front view, side profile, different ages) to increase matching accuracy.
        </p>

        <div className="p-4 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 text-blue-800 dark:text-blue-200 text-xs space-y-1">
          <p><strong>⭐ Quality Gate Requirement:</strong> Reference photos are automatically evaluated across Resolution, Focus Sharpness, and Lighting. Only photos with a <strong>4-star or 5-star rating</strong> are admitted into profiles, preventing blurry images from degrading scan accuracy.</p>
        </div>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">3. Multi-Reference Centroid Learning</h2>
        <p>
          As you add reference photos across different years, hairstyles, or lighting conditions, the engine automatically calculates a <strong>normalized mean centroid vector</strong>. This noise-smoothed identity representation allows the AI to recognize the person seamlessly whether in a photo from 2018 or 2026.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">4. 🧹 Clean Outliers &amp; Low-Star Images</h2>
        <p>
          If wrong photos were accidentally added during batch folder imports, click <strong>🧹 Clean Outliers</strong>. The engine will:
        </p>
        <ul className="list-disc list-inside space-y-1 pl-2 text-slate-600 dark:text-slate-400">
          <li>Remove any photo that does not match the core facial centroid (&lt; 60% similarity).</li>
          <li>Remove any low-quality or blurry photos (&lt; 4 stars).</li>
        </ul>
      </div>
    </div>
  );
}
