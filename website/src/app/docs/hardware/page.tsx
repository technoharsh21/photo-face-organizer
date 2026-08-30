export const metadata = {
  title: "Universal Hardware Acceleration | Photo Face Organizer Docs",
  description: "GPU acceleration via DirectML, CUDA, ROCm, CoreML, OpenVINO, and multi-core CPU scaling.",
};

export default function HardwareDocPage() {
  return (
    <div className="space-y-8 text-slate-700 dark:text-slate-300">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
        <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
          Performance &rsaquo; Hardware
        </span>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          Universal Hardware Acceleration Engine
        </h1>
        <p className="text-sm text-slate-500">
          Auto-configured GPU neural acceleration and high-throughput multi-core CPU scaling.
        </p>
      </div>

      <div className="space-y-6 text-sm leading-relaxed">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          1. Universal Multi-Architecture GPU Support
        </h2>
        <p>
          Photo Face Organizer is built on a <strong>Universal Hardware Provider Engine</strong> that automatically detects your physical graphics card and binds to the highest-performance acceleration backend available:
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1">
            <span className="text-xs font-mono font-bold text-brand-600 dark:text-brand-400">WINDOWS (ANY GPU)</span>
            <h4 className="font-bold text-slate-900 dark:text-white text-sm">DirectX 12 DirectML</h4>
            <p className="text-xs text-slate-500">Accelerates on NVIDIA GeForce/RTX, AMD Radeon, and Intel Arc / Iris Xe GPUs with zero complex driver installations.</p>
          </div>
          <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1">
            <span className="text-xs font-mono font-bold text-emerald-600 dark:text-emerald-400">NVIDIA WORKSTATIONS</span>
            <h4 className="font-bold text-slate-900 dark:text-white text-sm">CUDA &amp; TensorRT</h4>
            <p className="text-xs text-slate-500">Unlocks maximum throughput on NVIDIA cards utilizing dedicated Tensor Cores and FP16 neural precision.</p>
          </div>
          <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1">
            <span className="text-xs font-mono font-bold text-purple-600 dark:text-purple-400">APPLE SILICON (macOS)</span>
            <h4 className="font-bold text-slate-900 dark:text-white text-sm">CoreML Neural Engine</h4>
            <p className="text-xs text-slate-500">Binds directly to the 16-core Apple Neural Engine on M1, M2, M3, and M4 MacBooks and Macs with near-zero battery drain.</p>
          </div>
          <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1">
            <span className="text-xs font-mono font-bold text-amber-600 dark:text-amber-400">AMD LINUX &amp; INTEL</span>
            <h4 className="font-bold text-slate-900 dark:text-white text-sm">ROCm &amp; OpenVINO</h4>
            <p className="text-xs text-slate-500">Native compute execution on AMD ROCm Linux clusters and Intel Core/Xeon CPU architectures.</p>
          </div>
        </div>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          2. Concurrency &amp; 100% Compute Saturation
        </h2>
        <p>
          To prevent the common 10%&ndash;20% compute bottleneck, Photo Face Organizer uses an <strong>asynchronous producer-consumer worker pipeline</strong>:
        </p>
        <ul className="list-disc list-inside space-y-1.5 pl-2 text-slate-600 dark:text-slate-400">
          <li><strong>Unlocked Parallel Inference:</strong> Worker threads submit neural net forward passes concurrently across GPU compute streams without global lock contention.</li>
          <li><strong>Pipelined Image Decoding:</strong> Multi-threaded worker threads pre-decode raw DSLR, HEIC, and JPEG images in memory so the GPU is continuously saturated with zero idle wait time.</li>
        </ul>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          3. Specialized CPU vs. GPU Architecture
        </h2>
        <p>
          Tasks are assigned to the hardware component that executes them fastest:
        </p>
        <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-2 text-xs">
          <p>&bull; <strong>AI Face Vision (InsightFace ArcFace):</strong> Runs on the <strong>GPU</strong> for massively parallel neural tensor operations (50&ndash;200 photos/sec).</p>
          <p>&bull; <strong>Duplicate Photo Scanner (SHA-256):</strong> Runs on the <strong>CPU</strong> using built-in Intel SHA / AMD Zen cryptographic extensions directly from system RAM (1,000&ndash;5,000 photos/sec).</p>
        </div>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          4. Cascading Multi-Core CPU Fallback
        </h2>
        <p>
          If your computer does not have a dedicated GPU, or if GPU drivers are missing, the engine gracefully activates the <strong>Multi-Core CPU Provider</strong> without crashing, ensuring universal compatibility on all laptops and desktops.
        </p>
      </div>
    </div>
  );
}
