import Link from "next/link";

export const metadata = {
  title: "Photo Viewer & Lightbox | Photo Face Organizer Docs",
  description: "Full-screen lightbox for matched photos: zoom, rotate, keyboard navigation, per-photo match score, and one-click save or open location.",
};

export default function PhotoViewerDocPage() {
  return (
    <div className="space-y-8 text-slate-700 dark:text-slate-300">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
        <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
          Usage Guide &rsaquo; Reviewing Photos
        </span>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          Photo Viewer &amp; Lightbox
        </h1>
        <p className="text-sm text-slate-500">
          Review any matched photo at full resolution without leaving the app or opening an external image viewer.
        </p>
      </div>

      <div className="space-y-6 text-sm leading-relaxed">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          1. Where It Opens
        </h2>
        <p>
          The lightbox is the review surface for matched photos. Open it with the <strong>&#128269; View</strong> button on any result card in <Link href="/docs/find-photos">Find Photos by Person</Link>, or by selecting a photo in the Results output tree.
        </p>
        <p>
          The header always tells you which photo you are looking at and why it matched: the filename, a <strong>&#127919; N% Match</strong> badge with that photo&apos;s similarity score, and a <strong>&ldquo;3 of 148&rdquo;</strong> position counter so you know how much of the set remains.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          2. Keyboard Shortcuts
        </h2>
        <p>Browse a large result set entirely from the keyboard:</p>
        <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
          <table className="w-full text-xs">
            <thead className="bg-slate-100 dark:bg-slate-900 text-slate-700 dark:text-slate-300">
              <tr>
                <th className="px-4 py-2 text-left font-semibold">Key</th>
                <th className="px-4 py-2 text-left font-semibold">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-slate-600 dark:text-slate-400">
              <tr><td className="px-4 py-2 font-mono">&#8592; / &#8594;</td><td className="px-4 py-2">Previous / next photo</td></tr>
              <tr><td className="px-4 py-2 font-mono">+ / - (or scroll wheel)</td><td className="px-4 py-2">Zoom in / zoom out</td></tr>
              <tr><td className="px-4 py-2 font-mono">F or 0</td><td className="px-4 py-2">Fit to window</td></tr>
              <tr><td className="px-4 py-2 font-mono">1</td><td className="px-4 py-2">Actual size (100%)</td></tr>
              <tr><td className="px-4 py-2 font-mono">R or ]</td><td className="px-4 py-2">Rotate 90&deg; right</td></tr>
              <tr><td className="px-4 py-2 font-mono">L or [</td><td className="px-4 py-2">Rotate 90&deg; left</td></tr>
              <tr><td className="px-4 py-2 font-mono">Esc</td><td className="px-4 py-2">Close the viewer</td></tr>
            </tbody>
          </table>
        </div>
        <p>
          The same actions are available as toolbar buttons: <strong>&#10133;</strong> zoom in, <strong>&#10134;</strong> zoom out, <strong>&#8865;</strong> fit to window, <strong>&#10227;</strong> rotate, and <strong>&#10006;</strong> close.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          3. File Details &amp; Actions
        </h2>
        <p>
          Below the image, a status line reports the photo&apos;s full <strong>Path</strong>, pixel <strong>Size</strong>, and <strong>Modified</strong> timestamp &mdash; useful when two files share a name in different folders. Two buttons sit next to it:
        </p>
        <ul className="list-disc list-inside space-y-1.5 pl-2 text-slate-600 dark:text-slate-400">
          <li><strong>&#128194; Open Location</strong> &mdash; opens the operating system file manager at the photo&apos;s folder.</li>
          <li><strong>&#128190; Save Photo</strong> &mdash; copies just this photo somewhere else, leaving the original untouched.</li>
        </ul>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          4. Unreadable or Missing Files
        </h2>
        <p>
          The viewer never throws you out of the browse flow. If a file cannot be decoded, the header still shows the name and score and the detail line reads <em>&ldquo;(Unreadable image format)&rdquo;</em>; if the file has been moved since the search, it reads <em>&ldquo;File not found: &hellip;&rdquo;</em>. Arrow keys keep working either way, so you can step straight past the bad frame to the next match.
        </p>

        <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-400">
          &#128274; Every action here is read-only against your library. <strong>Open Location</strong> and <strong>Save Photo</strong> never modify, move, rename, or delete the source file.
        </div>
      </div>
    </div>
  );
}
