export const metadata = {
  title: "Creating Profiles & Reference Photos | Photo Face Organizer Docs",
  description: "Learn how to create individual and group profiles and add reference images.",
};

export default function ProfilesDocPage() {
  return (
    <div className="space-y-8 text-slate-700 dark:text-slate-300">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
        <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
          Usage Guide &rsaquo; Profiles
        </span>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          Creating People Profiles &amp; Reference Photos
        </h1>
        <p className="text-sm text-slate-500">
          How to build person profiles, upload reference photos, and configure face bounding boxes.
        </p>
      </div>

      <div className="space-y-6 text-sm leading-relaxed">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">1. Creating an Individual Profile</h2>
        <p>
          In the <strong>People Management</strong> section, click <strong>➕ Create Profile</strong>. Enter a person&apos;s name (e.g., &quot;Harsh&quot; or &quot;Alice&quot;) and select <strong>Individual Person Profile</strong>.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">2. Adding Reference Photos</h2>
        <p>
          Click <strong>📷 Add Reference Photo</strong> to upload clean images of the person. You can upload multiple reference photos from different angles (front view, side profile, different ages) to increase matching accuracy.
        </p>

        <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs">
          <strong>Multi-Face Selector:</strong> If a reference photo contains multiple detected faces, the application will display a face selector dialog prompting you to click on the exact target face to register.
        </div>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">3. Editing Profile Type</h2>
        <p>
          Click <strong>👥 Group Settings</strong> at the top right of any selected profile to update its name or convert it into a Group Profile.
        </p>
      </div>
    </div>
  );
}
