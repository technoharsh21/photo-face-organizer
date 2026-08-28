export const metadata = {
  title: "Hardware & Acceleration | Photo Face Organizer Docs",
  description: "CPU multi-threading and optional GPU hardware acceleration.",
};

export default function HardwareDocPage() {
  return (
    <div className="space-y-8 text-slate-700 dark:text-slate-300">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
        <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
          Performance &rsaquo; Hardware
        </span>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          Hardware &amp; Acceleration Modes
        </h1>
        <p className="text-sm text-slate-500">
          Understanding CPU multi-core processing and CUDA GPU hardware acceleration.
        </p>
      </div>

      <div className="space-y-6 text-sm leading-relaxed">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">1. CPU Mode (Default)</h2>
        <p>
          Photo Face Organizer is optimized to run efficiently on standard multi-core processors without requiring any discrete GPU. The engine distributes batch file reading and EXIF orientation transformations across available CPU worker threads.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">2. GPU Acceleration (CUDA)</h2>
        <p>
          If your system contains an NVIDIA GPU with CUDA support, the underlying dlib / OpenCV recognition models can utilize GPU acceleration for high-speed facial detection on large photo libraries.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">3. Automatic Hardware Fallback</h2>
        <p>
          If GPU acceleration is unavailable or encounters a memory error during heavy scans, the engine gracefully falls back to CPU execution without interrupting the active scan job.
        </p>
      </div>
    </div>
  );
}
