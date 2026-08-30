export const metadata = {
  title: "Face Quality Ratings & Outlier Purging | Photo Face Organizer Docs",
  description: "Learn how the 4 and 5-star quality gate and outlier cleaning algorithms protect recognition precision.",
};

export default function QualityRatingsDocPage() {
  return (
    <div className="space-y-8 text-slate-700 dark:text-slate-300">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
        <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
          Usage Guide &rsaquo; Quality &amp; Outliers
        </span>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          Face Quality Ratings &amp; Outlier Purging
        </h1>
        <p className="text-sm text-slate-500">
          How multi-dimensional quality scoring and automated outlier cleaning maintain 100% pure profile reference datasets.
        </p>
      </div>

      <div className="space-y-6 text-sm leading-relaxed">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          1. Why Face Quality Ratings Matter
        </h2>
        <p>
          AI facial recognition models (ArcFace) depend on clear, sharp facial landmarks (eyes, nose, mouth geometry). When reference photos contain motion blur, tiny 20-pixel crops, or severe shadows, the AI creates noisy embedding vectors that degrade scan accuracy.
        </p>
        <p>
          Photo Face Organizer evaluates every face crop across three independent physical dimensions:
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1.5">
            <h4 className="font-bold text-slate-900 dark:text-white text-sm">1. Face Resolution (45 pts)</h4>
            <p className="text-xs text-slate-500">Checks cropped face dimensions. Full HD/4K crops (&ge; 90px) score maximum points; tiny crops (&le; 25px) are penalised.</p>
          </div>
          <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1.5">
            <h4 className="font-bold text-slate-900 dark:text-white text-sm">2. Focus &amp; Sharpness (35 pts)</h4>
            <p className="text-xs text-slate-500">Computes OpenCV Laplacian variance (&sigma;&sup2;) across facial contours. Sharp eye/jaw edges score high; motion blur scores low.</p>
          </div>
          <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1.5">
            <h4 className="font-bold text-slate-900 dark:text-white text-sm">3. Lighting &amp; Exposure (20 pts)</h4>
            <p className="text-xs text-slate-500">Evaluates mean pixel brightness. Well-lit daylight and studio lighting score 20 pts; pitch black or overexposed faces score low.</p>
          </div>
        </div>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          2. The 1 to 5 Star Rating Scale
        </h2>
        <div className="space-y-2 font-mono text-xs">
          <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900 text-emerald-800 dark:text-emerald-200 flex items-center justify-between">
            <span>&bull; ⭐⭐⭐⭐⭐ (5/5 Stars: &ge; 78 pts)</span>
            <span className="font-semibold">Excellent: Studio Quality / Ultra Sharp</span>
          </div>
          <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900 text-blue-800 dark:text-blue-200 flex items-center justify-between">
            <span>&bull; ⭐⭐⭐⭐ (4/5 Stars: 58&ndash;77 pts)</span>
            <span className="font-semibold">Good: High Clarity &amp; Clean Contrast</span>
          </div>
          <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900 text-amber-800 dark:text-amber-200 flex items-center justify-between">
            <span>&bull; ⭐⭐⭐ (3/5 Stars: 40&ndash;57 pts)</span>
            <span className="font-semibold">Moderate: Slightly Soft / Medium Size (Rejected)</span>
          </div>
          <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900 text-rose-800 dark:text-rose-200 flex items-center justify-between">
            <span>&bull; ⭐⭐ / ⭐ (1&ndash;2 Stars: &lt; 40 pts)</span>
            <span className="font-semibold">Low: Tiny / Motion Blurred / Dark (Rejected)</span>
          </div>
        </div>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          3. Strict 4 &amp; 5-Star Quality Gates
        </h2>
        <ul className="list-disc list-inside space-y-1.5 pl-2 text-slate-600 dark:text-slate-400">
          <li><strong>Unknown Faces Vault:</strong> Low-quality bystander faces (&lt; 4 stars) are automatically discarded during scans so they don&apos;t clutter your unknown collection.</li>
          <li><strong>Profile Creation:</strong> When adding reference photos manually or converting unknown clusters, only 4-star and 5-star photos are permitted into person profiles.</li>
        </ul>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          4. 1-Click &quot;Clean Outliers&quot; Feature
        </h2>
        <p>
          On any person profile, clicking <strong>🧹 Clean Outliers</strong> automatically performs a dual-cleaning pass:
        </p>
        <ol className="list-decimal list-inside space-y-1.5 pl-2 text-slate-600 dark:text-slate-400">
          <li><strong>Identity Outlier Purging:</strong> Calculates the mathematical centroid vector of the profile and removes any photo with similarity &lt; 60% (e.g. accidentally added friends/strangers).</li>
          <li><strong>Low-Star Image Purging:</strong> Automatically removes any degraded or blurry reference photos scoring &lt; 4 stars.</li>
        </ol>
      </div>
    </div>
  );
}
