export const metadata = {
  title: "Live Camera Face Enrollment | Photo Face Organizer Docs",
  description: "Train a profile straight from your webcam with the 360° multi-angle face scanner, including hands-free auto-capture gated on 4-star face quality.",
};

export default function LiveEnrollmentDocPage() {
  return (
    <div className="space-y-8 text-slate-700 dark:text-slate-300">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
        <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
          Usage Guide &rsaquo; Face Enrollment
        </span>
        <h1 className="text-xl sm:text-3xl font-extrabold text-slate-900 dark:text-white">
          360&deg; Live Camera Face Enrollment
        </h1>
        <p className="text-sm text-slate-500">
          Train a new profile from a webcam instead of hunting for five good photos &mdash; with an optional hands-free mode that shoots each angle for you.
        </p>
      </div>

      <div className="space-y-6 text-sm leading-relaxed">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          1. Why Multiple Angles?
        </h2>
        <p>
          A profile trained on one front-facing photo recognizes a front-facing person &mdash; and quietly misses them in side-profile, chin-up, or smiling photos. The scanner captures <strong>5 diverse face angles (Front, Left, Right, Up, Smile)</strong>, so the resulting <strong>512-dimensional ArcFace</strong> vectors cover the way people actually appear in real albums.
        </p>
        <p>
          Open it from <strong>&#128101; People Profiles</strong> when creating or editing a profile, using the <strong>&#127909; Scan with Camera</strong> button. The dialog is titled <em>&ldquo;&#127909; 360&deg; Live Face Scanner &amp; Enrollment&rdquo;</em>.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          2. The Five Guided Angles
        </h2>
        <p>Each step shows an icon, an instruction line, and a thumbnail strip of which angles are still missing:</p>
        <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-2 text-xs">
          <p>&#128247; <strong>Step 1/5 &mdash; Look Straight:</strong> Look directly at the camera with a neutral face.</p>
          <p>&#128072; <strong>Step 2/5 &mdash; Turn Left:</strong> Turn your head slightly to the left (about 30&deg;).</p>
          <p>&#128073; <strong>Step 3/5 &mdash; Turn Right:</strong> Turn your head slightly to the right (about 30&deg;).</p>
          <p>&#128070; <strong>Step 4/5 &mdash; Tilt Up:</strong> Slightly tilt your chin up towards the ceiling.</p>
          <p>&#128522; <strong>Step 5/5 &mdash; Smile / Expression:</strong> Give a natural smile or look slightly tilted.</p>
        </div>
        <p>
          Use <strong>&#128247; Capture Photo</strong> to shoot the current angle, <strong>&#128257; Retake Angle</strong> to discard a bad frame and redo it, and <strong>&#9989; Finish &amp; Enroll 360&deg; Profile</strong> when all five are in.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          3. Hands-Free Auto Capture
        </h2>
        <p>
          Two automation levels exist so you never have to reach for the mouse mid-pose:
        </p>
        <ul className="list-disc list-inside space-y-1.5 pl-2 text-slate-600 dark:text-slate-400">
          <li><strong>&#9889; Auto-Capture (3s)</strong> &mdash; a timed countdown shoots the angle you are currently on.</li>
          <li><strong>&#9889; Auto Scan: OFF / ON</strong> &mdash; fully hands-free. Toggle it on and the scanner watches the camera and fires each shot itself; the button turns green, and the manual capture buttons are disabled while it owns the shutter.</li>
        </ul>
        <p>
          Auto Scan decides when to shoot from live geometry rather than a timer. Each frame&apos;s <strong>5 facial keypoints</strong> are classified into a pose bucket (chin-up first, then yaw left/right, then a wide-mouth smile, otherwise frontal), and a shot fires only when:
        </p>
        <ul className="list-disc list-inside space-y-1.5 pl-2 text-slate-600 dark:text-slate-400">
          <li>the head has held that <strong>same pose stable for 12 consecutive frames</strong>, so a mid-turn blur never gets captured;</li>
          <li>the frame passes the <strong>same 4-star quality gate</strong> used for reference photos (resolution, Laplacian sharpness, lighting);</li>
          <li>that angle has <strong>not already been captured</strong>, and the short post-capture cooldown has expired.</li>
        </ul>
        <p>
          When the final bucket is filled the button reads <em>&ldquo;&#9989; All angles captured!&rdquo;</em> and enrollment completes on its own &mdash; no click required.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          4. Camera Requirements
        </h2>
        <ul className="list-disc list-inside space-y-1.5 pl-2 text-slate-600 dark:text-slate-400">
          <li>Any standard webcam the operating system can open; if none is found the dialog reports <em>&ldquo;&#9888;&#65039; No webcam detected. Please connect a USB camera and try again.&rdquo;</em> and the rest of the app keeps working.</li>
          <li>Indirect, even lighting beats a bright direct source &mdash; the lighting component of the quality gate penalises both washed-out and near-black frames.</li>
          <li>Angles already captured manually are remembered if you switch to Auto Scan part-way through, so it fills only what is missing.</li>
          <li>The camera is released as soon as the dialog closes; the app does not hold the device open in the background.</li>
        </ul>

        <div className="p-4 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 text-blue-800 dark:text-blue-200 text-sm">
          &#128274; <strong>Nothing leaves your machine.</strong> The camera stream is processed in memory by the local InsightFace engine and never written to disk or uploaded. Only the five selected captures are stored, inside your local profile folder.
        </div>
      </div>
    </div>
  );
}
