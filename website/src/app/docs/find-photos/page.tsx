import Link from "next/link";

export const metadata = {
  title: "Find Photos by Person | Photo Face Organizer Docs",
  description: "Instantly discover every photo of any person across your folders with real-time match streaming, Solo vs All matching, and a built-in lightbox.",
};

export default function FindPhotosDocPage() {
  return (
    <div className="space-y-8 text-slate-700 dark:text-slate-300">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
        <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
          Usage Guide &rsaquo; Find Photos
        </span>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          Find Photos by Person
        </h1>
        <p className="text-sm text-slate-500">
          Search any folder for every photo of a specific person &mdash; without running an organizing scan or creating any output folders.
        </p>
      </div>

      <div className="space-y-6 text-sm leading-relaxed">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          1. How This Differs From a Scan
        </h2>
        <p>
          The <strong>New Scan Wizard</strong> and <strong>Solo Scan</strong> copy matched photos into an output directory. <strong>Find Photos by Person</strong> is a read-only search: it streams matches onto the screen and only writes to disk if you explicitly choose which photos to save.
        </p>
        <ul className="list-disc list-inside space-y-1.5 pl-2 text-slate-600 dark:text-slate-400">
          <li><strong>No output folder required.</strong> Nothing is created or moved while you search.</li>
          <li><strong>Results appear while it works.</strong> Each match is rendered into the gallery the moment it is found &mdash; you do not wait for the whole folder set to finish.</li>
          <li><strong>Reusable.</strong> Run it again for another person, or hit <strong>&#128257; New Search</strong> to restart the wizard.</li>
        </ul>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          2. The Four-Step Workflow
        </h2>
        <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-2 text-xs">
          <p className="font-semibold text-slate-800 dark:text-slate-200">Step 1 &mdash; Select a Person to Find</p>
          <p>A searchable grid of your profile cards (avatar, name, reference-photo count). Type in <em>&ldquo;Search people by name&hellip;&rdquo;</em> to filter, then click a card; it is marked <strong>&#10003; Selected</strong>.</p>
          <p className="font-semibold text-slate-800 dark:text-slate-200 pt-2">Step 2 &mdash; Select Folders</p>
          <p>&bull; <strong>&#128193; Choose Folder</strong> to pick one directory.<br />&bull; <strong>&#10133; Add Another Folder</strong> to stack several sources into one search.<br />&bull; <strong>&#128465; Clear All</strong> to reset.<br />&bull; <strong>&#128453;&#65039; Include subdirectories (Recursive)</strong> is enabled by default.</p>
          <p className="font-semibold text-slate-800 dark:text-slate-200 pt-2">Step 3 &mdash; Choose Photo Matching Type</p>
          <p>Pick one of the two mode cards (see section 3), then review the <strong>&#128203; Search Configuration Summary</strong> listing Person, Folders, and Mode before clicking <strong>&#128640; Start Finding Photos</strong>.</p>
          <p className="font-semibold text-slate-800 dark:text-slate-200 pt-2">Step 4 &mdash; Live Results Gallery</p>
          <p>Matched thumbnails stream in with their similarity score. See section 4.</p>
        </div>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          3. Solo Photos vs All Photos
        </h2>
        <p>
          Step 3 decides how strict the person-count rule is:
        </p>
        <ul className="list-disc list-inside space-y-1.5 pl-2 text-slate-600 dark:text-slate-400">
          <li><strong>All Photos (Solo + Group Photos)</strong> &mdash; badge <em>&ldquo;&#10024; Complete Collection&rdquo;</em>, and the default. Returns <strong>every</strong> photo where at least one detected face matches the selected person, including family portraits and crowd shots.</li>
          <li><strong>Solo Photos Only</strong> &mdash; badge <em>&ldquo;&#127919; 0% Other Faces&rdquo;</em>. Returns only photos where the person is completely alone; any photo where <strong>2 or more faces</strong> are detected is excluded outright, regardless of how well the person matches.</li>
        </ul>
        <p>
          Both modes use the same <strong>Default Matching Precision Threshold</strong> from Settings, and both report a <strong>&#127919; N%</strong> badge on every result so you can see match confidence per photo.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          4. Controlling the Live Search
        </h2>
        <p>
          While searching, the header reports <strong>&#128194; Scanned: current / total</strong>, <strong>&#10024; Matches Found</strong>, and <strong>&#9201;&#65039; Elapsed</strong>, plus the file currently being read. Three controls are available:
        </p>
        <ul className="list-disc list-inside space-y-1.5 pl-2 text-slate-600 dark:text-slate-400">
          <li><strong>&#9208;&#65039; Pause / &#9654;&#65039; Resume</strong> &mdash; freeze the search and inspect the matches found so far, then continue.</li>
          <li><strong>&#128681; Stop Search</strong> &mdash; end early; matches already discovered stay in the gallery and are still saveable.</li>
          <li>On completion the header reads <em>&ldquo;&#127881; Search Complete! Found N photos of &lt;Name&gt; (&lt;seconds&gt;s)&rdquo;</em>. If nothing matched, it says so and suggests scanning more folders or adding clearer reference photos.</li>
        </ul>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          5. Inspecting &amp; Saving Results
        </h2>
        <p>
          Every result card has a <strong>&#128269; View</strong> button (opens the <Link href="/docs/photo-viewer">lightbox viewer</Link>), a <strong>&#128190; Save</strong> button, and a selection checkbox. A hover tooltip shows the full path, match percentage, and file modification date.
        </p>
        <p>
          The batch bar provides <strong>&#9744;&#65039; Select All</strong>, <strong>&#9723;&#65039; Deselect All</strong>, a live &ldquo;<em>N selected</em>&rdquo; counter, <strong>&#128190; Save Selected (N)</strong>, and <strong>&#128230; Save All Matches (N)</strong>. Saving asks you for a destination folder, resolves filename collisions automatically, and <strong>copies</strong> files &mdash; your originals are never moved, renamed, or deleted.
        </p>

        <div className="p-4 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 text-blue-800 dark:text-blue-200 text-sm">
          &#128161; <strong>Scanning boundary:</strong> Find Photos walks only the folders you added (and their subfolders when recursive is on). Symbolic links are not followed and resolved paths outside your selected folders are rejected, so a stray symlink cannot pull the search outside the boundary you chose.
        </div>
      </div>
    </div>
  );
}
