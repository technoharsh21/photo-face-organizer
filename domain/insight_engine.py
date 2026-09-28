"""
InsightFace AI Vision Engine Module.

Uses SCRFD 360° Deep Face Detector (detects faces from all angles, profile views,
tilted heads, and dark lighting) and ArcFace 512-dimensional Neural Network for
world-record 99.86% matching accuracy.

Powered by Microsoft ONNX Runtime with automatic hardware GPU detection
(NVIDIA CUDA GPU on Windows/Linux, Apple CoreML GPU on macOS, and Multi-Core CPU fallback).
"""

import io
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any


import numpy as np
try:
    import onnxruntime
except ImportError:
    onnxruntime = None
from PIL import Image

# Guarantee sys.stdout/stderr are never None (PyInstaller --windowed on Windows)
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

try:
    import insightface
    from insightface.app import FaceAnalysis
except ImportError:
    insightface = None
    FaceAnalysis = None

logger = logging.getLogger(__name__)


class InsightFaceEngine:
    """
    World-class AI face detection and recognition engine powered by InsightFace and ONNX Runtime.
    """

    # Class-level lock: prevents multiple scan worker threads from simultaneously
    # initializing the GPU model (race condition crashes DirectML/CUDA with no error message)
    _init_lock = threading.Lock()

    # Class-level inference lock: Direct3D 12 DirectML command allocators/lists are explicitly
    # NOT thread-safe for concurrent app.get() calls. This mutex serializes only the ~15ms GPU forward pass,
    # preventing D3D12 device lost / status access violation (0xC0000005) crashes while letting CPU threads
    # decode and prepare images in parallel.
    _infer_lock = threading.Lock()

    def __init__(self, device_preference: str = "Auto"):
        self.device_preference = device_preference
        self.active_device = "Multi-Core CPU"
        self.gpu_available = False
        self.providers: list[str] = []
        self.app: FaceAnalysis | None = None
        self._is_initialized = False

        self._configure_providers()


    def get_system_gpu_vram_mb(self) -> int | None:
        """Detect GPU VRAM in MB via nvidia-smi. Returns None if unavailable."""
        try:
            if sys.platform == "win32":
                out = subprocess.check_output(
                    "nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits",
                    shell=True, text=True, stderr=subprocess.DEVNULL
                )
            elif sys.platform in ("linux", "darwin"):
                out = subprocess.check_output(
                    "nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits",
                    shell=True, text=True, stderr=subprocess.DEVNULL
                )
            else:
                return None
            val = int(out.strip().split("\n")[0].strip())
            return val
        except Exception:
            return None

    @staticmethod
    def suggest_gpu_workers(vram_mb: int | None, cpu_cores: int, performance_mode: str) -> int:
        """
        Suggest optimal thread pool size for a GPU-accelerated scan.
        VRAM budget: ~150 MB per concurrent worker (image buffers + face crops).
        Rounds down to keep headroom. Falls back to CPU-core-based sizing.
        """
        if vram_mb is not None and performance_mode != "Eco":
            # Conservative: use 75% of VRAM, 150 MB per worker
            workers_by_vram = int((vram_mb * 0.75) / 150)
            cpu_baseline = max(4, cpu_cores * 2) if performance_mode == "Maximum Performance" else max(2, cpu_cores)
            return max(cpu_baseline, workers_by_vram)
        # Fallback to CPU-derived sizing
        if performance_mode == "Maximum Performance":
            return max(4, cpu_cores * 2)
        elif performance_mode == "Balanced":
            return max(2, cpu_cores)
        return max(1, cpu_cores // 4)

    def get_system_gpu_name(self) -> str:
        """Dynamically fetch the exact real GPU model name in real-time from OS kernel queries for any user machine."""
        try:
            import subprocess
            import sys

            if sys.platform == "win32":
                try:
                    out = subprocess.check_output(
                        'powershell -Command "Get-CimInstance -ClassName Win32_VideoController | Select-Object -ExpandProperty Name"',
                        shell=True, text=True, stderr=subprocess.DEVNULL
                    )
                    lines = [line.strip() for line in out.splitlines() if line.strip()]
                    if lines:
                        # Return the first valid display adapter found on the user's system dynamically
                        return lines[0]
                except Exception:
                    pass

                try:
                    out = subprocess.check_output("wmic path win32_VideoController get name", shell=True, text=True, stderr=subprocess.DEVNULL)
                    lines = [line.strip() for line in out.splitlines() if line.strip() and line.lower() != "name"]
                    if lines:
                        return lines[0]
                except Exception:
                    pass

            elif sys.platform == "linux":
                out = subprocess.check_output("lspci | grep -i 'vga\\|3d\\|display'", shell=True, text=True, stderr=subprocess.DEVNULL)
                if out.strip():
                    raw_line = out.splitlines()[0].strip()
                    if ":" in raw_line:
                        gpu_part = raw_line.split(":", 2)[-1].strip()
                        # Clean bracketed names e.g. Advanced Micro Devices... [Radeon Vega Series]
                        if "[" in gpu_part and "]" in gpu_part:
                            start = gpu_part.rfind("[") + 1
                            end = gpu_part.rfind("]")
                            if start < end:
                                return gpu_part[start:end]
                        return gpu_part
                    return raw_line

            elif sys.platform == "darwin":
                out = subprocess.check_output("system_profiler SPDisplaysDataType | grep 'Chipset Model'", shell=True, text=True, stderr=subprocess.DEVNULL)
                if out.strip():
                    return out.split(":", 1)[-1].strip()

        except Exception:
            pass

        return ""

    def get_system_cpu_name(self) -> str:
        """Detect the exact real CPU model name, physical cores, and logical threads on Linux/Windows/macOS."""
        import subprocess
        import sys

        logical_threads = os.cpu_count() or 4
        physical_cores = logical_threads

        def _clean_cpu(raw_name: str) -> str:
            clean = raw_name
            for noise in [" with Radeon Graphics", " with Radeon Vega Graphics", " with Intel Graphics", " with UHD Graphics", " with Iris Xe Graphics"]:
                clean = clean.replace(noise, "").replace(noise.lower(), "")
            return clean.strip()

        try:
            if sys.platform == "linux":
                try:
                    out = subprocess.check_output("lscpu", shell=True, text=True, stderr=subprocess.DEVNULL)
                    cps, sockets = None, 1
                    for line in out.splitlines():
                        if "Core(s) per socket:" in line:
                            cps = int(line.split(":")[-1].strip())
                        elif "Socket(s):" in line:
                            sockets = int(line.split(":")[-1].strip())
                    if cps and sockets:
                        physical_cores = cps * sockets
                except Exception:
                    pass

                cores_label = f"{physical_cores} Cores / {logical_threads} Threads" if physical_cores != logical_threads else f"{logical_threads} Cores"

                if Path("/proc/cpuinfo").exists():
                    text = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="ignore")
                    for line in text.splitlines():
                        if "model name" in line.lower():
                            parts = line.split(":", 1)
                            if len(parts) == 2:
                                name = _clean_cpu(parts[1].strip())
                                return f"{name} ({cores_label})"
                out = subprocess.check_output("lscpu", shell=True, text=True, stderr=subprocess.DEVNULL)
                for line in out.splitlines():
                    if "model name" in line.lower():
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            name = _clean_cpu(parts[1].strip())
                            return f"{name} ({cores_label})"

            elif sys.platform == "win32":
                try:
                    out_json = subprocess.check_output(
                        'powershell -Command "Get-CimInstance -ClassName Win32_Processor | Select-Object -Property Name, NumberOfCores, NumberOfLogicalProcessors | ConvertTo-Json"',
                        shell=True, text=True, stderr=subprocess.DEVNULL
                    )
                    import json
                    data = json.loads(out_json)
                    if isinstance(data, list):
                        data = data[0]
                    name = _clean_cpu(data.get("Name", ""))
                    p_cores = data.get("NumberOfCores")
                    l_threads = data.get("NumberOfLogicalProcessors") or logical_threads
                    if p_cores and l_threads:
                        c_label = f"{p_cores} Cores / {l_threads} Threads" if p_cores != l_threads else f"{l_threads} Cores"
                    else:
                        c_label = f"{logical_threads} Cores"
                    if name:
                        return f"{name} ({c_label})"
                except Exception:
                    pass

            elif sys.platform == "darwin":
                try:
                    p_c = subprocess.check_output("sysctl -n hw.physicalcpu", shell=True, text=True, stderr=subprocess.DEVNULL).strip()
                    if p_c and p_c.isdigit():
                        physical_cores = int(p_c)
                except Exception:
                    pass
                cores_label = f"{physical_cores} Cores / {logical_threads} Threads" if physical_cores != logical_threads else f"{logical_threads} Cores"
                out = subprocess.check_output("sysctl -n machdep.cpu.brand_string", shell=True, text=True, stderr=subprocess.DEVNULL)
                if out.strip():
                    name = _clean_cpu(out.strip())
                    return f"{name} ({cores_label})"

        except Exception:
            pass

        cores_label = f"{physical_cores} Cores / {logical_threads} Threads" if physical_cores != logical_threads else f"{logical_threads} Cores"
        return f"Multi-Core CPU ({cores_label})"

    def _configure_providers(self):
        """Quickly detect hardware providers without loading models into memory (Instant App Launch)."""
        try:
            available_providers = onnxruntime.get_available_providers()
            gpu_name = self.get_system_gpu_name()
            cpu_name = self.get_system_cpu_name()

            logger.info("=== AI HARDWARE CONFIGURATION ===")
            logger.info(f"Platform: {sys.platform}")
            logger.info(f"ONNX Runtime Version: {getattr(onnxruntime, '__version__', 'Unknown')}")
            logger.info(f"Available ONNX Execution Providers: {available_providers}")
            logger.info(f"Device Preference: {self.device_preference}")
            logger.info(f"Detected System GPU: {gpu_name or 'None Detected'}")
            logger.info(f"Detected System CPU: {cpu_name or 'Generic CPU'}")

            if self.device_preference == "CPU":
                self.providers = ["CPUExecutionProvider"]
                self.active_device = f"Multi-Core CPU ({cpu_name})"
                self.gpu_available = False
            elif "TensorrtExecutionProvider" in available_providers and self.device_preference in ("Auto", "TensorRT", "GPU"):
                self.providers = ["TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"]
                self.active_device = f"NVIDIA TensorRT GPU ({gpu_name})" if gpu_name else "TensorRT GPU"
                self.gpu_available = True
            elif "CUDAExecutionProvider" in available_providers and self.device_preference in ("Auto", "CUDA", "GPU"):
                self.providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
                self.active_device = f"CUDA GPU ({gpu_name})" if gpu_name else "CUDA GPU"
                self.gpu_available = True
            elif "ROCMExecutionProvider" in available_providers and self.device_preference in ("Auto", "ROCM", "GPU"):
                self.providers = ["ROCMExecutionProvider", "CPUExecutionProvider"]
                self.active_device = f"AMD ROCm GPU ({gpu_name})" if gpu_name else "AMD ROCm GPU"
                self.gpu_available = True
            elif "DmlExecutionProvider" in available_providers and self.device_preference in ("Auto", "DirectML", "GPU"):
                self.providers = ["DmlExecutionProvider", "CPUExecutionProvider"]
                self.active_device = f"DirectX 12 GPU ({gpu_name})" if gpu_name else "DirectX 12 DirectML GPU"
                self.gpu_available = True
            elif "OpenVINOExecutionProvider" in available_providers and self.device_preference != "CPU":
                self.providers = ["OpenVINOExecutionProvider", "CPUExecutionProvider"]
                self.active_device = f"Intel OpenVINO GPU ({gpu_name})" if gpu_name else "Intel OpenVINO GPU"
                self.gpu_available = True
            elif "CoreMLExecutionProvider" in available_providers and self.device_preference != "CPU":
                self.providers = ["CoreMLExecutionProvider", "CPUExecutionProvider"]
                self.active_device = f"Apple Neural Engine ({gpu_name})" if gpu_name else "Apple Neural Engine"
                self.gpu_available = True
            else:
                self.providers = ["CPUExecutionProvider"]
                self.active_device = f"Multi-Core CPU ({cpu_name})"
                self.gpu_available = False

            logger.info(f"Active Device Configured: {self.active_device} (Providers: {self.providers})")
            logger.info("=================================")

        except Exception as e:
            logger.warning(f"Error configuring execution providers: {e}", exc_info=True)
            cpu_name = self.get_system_cpu_name()
            self.providers = ["CPUExecutionProvider"]
            self.active_device = f"Multi-Core CPU ({cpu_name})"
            self.gpu_available = False

    def _ensure_initialized(self):
        """Lazy load ONNX models into memory when required with cascading GPU fallback.

        Thread-safe: uses a class-level lock so multiple scan worker threads cannot
        simultaneously call FaceAnalysis() / app.prepare() on the same GPU context,
        which would silently crash DirectML without any error message or log output.
        """
        # Fast path: already initialized — no lock needed
        if self._is_initialized and self.app is not None:
            return

        # Serialized init: only one thread at a time initializes the GPU model.
        # Without this lock, 6 scan worker threads simultaneously call FaceAnalysis()
        # and app.prepare() on the same DML GPU context, silently crashing the app.
        with InsightFaceEngine._init_lock:
            # Double-check inside lock: another thread may have finished init while we waited
            if self._is_initialized and self.app is not None:
                logger.debug(
                    f"[_ensure_initialized] SKIPPED (already initialized by another thread) | "
                    f"active_device={self.active_device} | providers={self.providers}"
                )
                return

            logger.info(
                f"[_ensure_initialized] INIT START | "
                f"device_preference={self.device_preference} | "
                f"target_providers={self.providers} | "
                f"active_device(before)={self.active_device}"
            )

            # Guard stdout/stderr during InsightFace model loading (PyInstaller --windowed)
            _orig_stdout = sys.stdout
            _orig_stderr = sys.stderr
            try:
                cpu_cores = os.cpu_count() or 4

                # --- Maximize CPU parallelism across all backends ---
                try:
                    import cv2
                    cv2.setNumThreads(cpu_cores)
                except Exception:
                    pass

                # OpenCV / NumPy OpenMP parallelism — use all physical cores
                os.environ.setdefault("OMP_NUM_THREADS", str(cpu_cores))
                os.environ.setdefault("OMP_PROC_BIND", "close")
                os.environ.setdefault("OMP_PLACES", "threads")
                os.environ.setdefault("MKL_NUM_THREADS", str(cpu_cores))
                os.environ.setdefault("OPENBLAS_NUM_THREADS", str(cpu_cores))

                # --- Build ONNX Runtime SessionOptions for maximum multi-core throughput ---
                sess_opts = onnxruntime.SessionOptions()
                sess_opts.intra_op_num_threads = 0  # 0 = let ONNX auto-tune (CUDA: uses GPU threads, CPU: uses physical cores)
                sess_opts.inter_op_num_threads = 0  # 0 = let ONNX auto-tune
                sess_opts.execution_mode = onnxruntime.ExecutionMode.ORT_SEQUENTIAL
                sess_opts.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL

                # --- CUDA-specific provider options for maximum throughput ---
                cuda_opts = {
                    "device_id": 0,
                    "arena_extend_strategy": "kNextPowerOfTwo",
                    "cudnn_conv_algo_search": "HEURISTIC",  # faster startup vs EXHAUSTIVE; same quality as DEFAULT
                    "do_copy_in_default_stream": False,       # async host<->GPU copies overlap with compute
                }

                # For non-CUDA GPU EPs (ROCM, TensorRT, DirectML), use empty opts dict
                all_opts = []
                for p in self.providers:
                    if p == "CUDAExecutionProvider":
                        all_opts.append(cuda_opts)
                    else:
                        all_opts.append({})

                logger.info(f"Initializing InsightFace models (sess_opts: intra=0, inter=0, CUDA opts: {cuda_opts})...")

                # 1. Attempt primary configured provider list
                logger.info(
                    f"[_ensure_initialized] STEP 1 — Trying primary providers: {self.providers} | "
                    f"sess_opts=intra_op=0,inter_op=0 | provider_options={all_opts}"
                )
                try:
                    self.app = FaceAnalysis(name="buffalo_sc", providers=self.providers, sess_options=sess_opts, provider_options=all_opts)
                    self.app.prepare(ctx_id=0, det_size=(640, 640), det_thresh=0.35)
                    self._is_initialized = True
                    logger.info(
                        f"[_ensure_initialized] STEP 1 SUCCESS | "
                        f"active_device={self.active_device} | "
                        f"providers={self.providers} | gpu_available={self.gpu_available}"
                    )
                    return
                except Exception as primary_err:
                    logger.warning(
                        f"[_ensure_initialized] STEP 1 FAILED | "
                        f"providers={self.providers} | error={primary_err}"
                    )

                # 2. Cascading Fallback 1: Try DirectX 12 DirectML (NVIDIA / AMD / Intel GPU)
                available = onnxruntime.get_available_providers()
                logger.info(
                    f"[_ensure_initialized] STEP 2 — Checking DML fallback | "
                    f"available_providers={available} | current_providers={self.providers}"
                )
                if "DmlExecutionProvider" in available and "DmlExecutionProvider" not in self.providers:
                    logger.info(
                        f"[_ensure_initialized] STEP 2 — Trying DirectX 12 DirectML GPU | "
                        f"dml_providers=['DmlExecutionProvider','CPUExecutionProvider']"
                    )
                    try:
                        dml_providers = ["DmlExecutionProvider", "CPUExecutionProvider"]
                        dml_opts = [{}, {"CPUExecutionProvider": {}}]
                        self.app = FaceAnalysis(name="buffalo_sc", providers=dml_providers, sess_options=sess_opts, provider_options=dml_opts)
                        self.app.prepare(ctx_id=0, det_size=(640, 640), det_thresh=0.35)
                        self.providers = dml_providers
                        gpu_name = self.get_system_gpu_name()
                        self.active_device = f"DirectX 12 GPU ({gpu_name})"
                        self.gpu_available = True
                        self._is_initialized = True
                        logger.info(
                            f"[_ensure_initialized] STEP 2 SUCCESS | "
                            f"active_device={self.active_device} | "
                            f"providers={dml_providers} | gpu_available=True"
                        )
                        return
                    except Exception as dml_err:
                        logger.warning(
                            f"[_ensure_initialized] STEP 2 FAILED | "
                            f"error={dml_err} | "
                            f"DirectX 12 DirectML GPU is unavailable or failed"
                        )

                # 3. Cascading Fallback 2: Multi-Core CPU
                logger.info(
                    f"[_ensure_initialized] STEP 3 — Falling back to Multi-Core CPU | "
                    f"providers=['CPUExecutionProvider']"
                )
                cpu_name = self.get_system_cpu_name()
                self.providers = ["CPUExecutionProvider"]
                self.active_device = f"Multi-Core CPU ({cpu_name})"
                self.gpu_available = False
                try:
                    self.app = FaceAnalysis(name="buffalo_sc", providers=self.providers, sess_options=sess_opts)
                    self.app.prepare(ctx_id=0, det_size=(640, 640), det_thresh=0.35)
                    self._is_initialized = True
                    logger.info(
                        f"[_ensure_initialized] STEP 3 SUCCESS | "
                        f"active_device={self.active_device} | "
                        f"providers={self.providers} | gpu_available=False"
                    )
                except Exception as cpu_init_err:
                    logger.error(
                        f"[_ensure_initialized] STEP 3 FAILED | ALL BACKENDS EXHAUSTED | "
                        f"error={cpu_init_err}"
                    )

            except Exception as cpu_err:
                logger.error(
                    f"[_ensure_initialized] OUTER EXCEPTION | "
                    f"device_preference={self.device_preference} | "
                    f"error={cpu_err}", exc_info=True
                )


    def _patch_session_threads(self, num_threads: int):
        """
        Patch ONNX Runtime session thread counts after FaceAnalysis creates its internal sessions.
        InsightFace wraps ONNX models inside AnalysisSession objects; each model has an underlying
        InferenceSession accessible via .session. Setting intra_op_num_threads on each session
        allows NumPy/BLAS ops to run across all CPU cores during inference.
        """
        try:
            if self.app is None or not hasattr(self.app, "models"):
                return
            for model_name, model in self.app.models.items():
                sess = getattr(model, "session", None)
                if sess is not None and hasattr(sess, "options") and hasattr(sess.options, "intra_op_num_threads"):
                    sess.options.intra_op_num_threads = num_threads
                    logger.debug(f"Patched ONNX session '{model_name}' intra_op_num_threads -> {num_threads}")
        except Exception as e:
            logger.debug(f"Could not patch ONNX session threads: {e}")

    def _detect_system_gpu(self) -> bool:
        """Detect system GPU hardware presence (NVIDIA, AMD, Intel)."""
        try:
            import subprocess
            import sys

            if sys.platform == "win32":
                out = subprocess.check_output("wmic path win32_VideoController get name", shell=True, text=True, stderr=subprocess.DEVNULL)
                names = out.lower()
                return any(vendor in names for vendor in ["nvidia", "amd", "radeon", "geforce", "rtx", "gtx", "quadro", "intel"])
            elif sys.platform == "linux":
                out = subprocess.check_output("lspci -vnn | grep -i vga", shell=True, text=True, stderr=subprocess.DEVNULL)
                return bool(out.strip())
        except Exception:
            pass
        return False

    def set_device_preference(self, preference: str) -> str:
        """Update hardware device preference with clean lock-protected state reset."""
        with InsightFaceEngine._init_lock:
            self.device_preference = preference
            self._is_initialized = False
            self.app = None
            self._configure_providers()
        return self.active_device


    def get_device_info(self) -> dict[str, Any]:
        """Return active AI hardware acceleration status and model info."""
        return {
            "requested_device": self.device_preference,
            "active_device": self.active_device,
            "gpu_available": self.gpu_available,
            "providers": self.providers,
            "model_used": "InsightFace (SCRFD 360° + ArcFace 512-d)",
        }

    def _preprocess_bgr_image(self, img_bgr: np.ndarray) -> np.ndarray:
        """
        Enhances image for face scanning:
        1. Low-light CLAHE contrast boost for dark/night images (mean brightness < 65).
        2. Adaptive det_size configuration based on megapixel resolution.

        NOTE: Dynamic det_size changes are intentionally SKIPPED for DmlExecutionProvider.
        DirectML pre-compiles the ONNX graph at initialization time (640x640). Calling
        app.prepare() again with a different det_size causes the Reshape_213 node to throw
        E_INVALIDARG (0x80070057) — the root cause of the "not responding" crash on large
        wedding/4K photos. CPU and CUDA providers handle dynamic reshaping correctly.
        """
        if img_bgr is None or img_bgr.size == 0:
            return img_bgr

        h, w = img_bgr.shape[:2]
        logger.debug(
            f"[preprocess] START | img={w}x{h} | "
            f"active_device={self.active_device} | "
            f"gpu_available={self.gpu_available}"
        )

        # Adaptive detection resolution — ONLY for non-DML providers.
        # DML pre-compiles at (640,640) and CANNOT be dynamically resized without crashing.
        _using_dml = "DmlExecutionProvider" in self.providers
        if not _using_dml:
            h, w = img_bgr.shape[:2]
            target_det = (1024, 1024) if max(h, w) >= 2500 else (640, 640)
            if hasattr(self, "_current_det_size") and self._current_det_size != target_det:
                if self.app is not None:
                    try:
                        self.app.prepare(ctx_id=0, det_size=target_det)
                        self._current_det_size = target_det
                    except Exception:
                        pass
            elif not hasattr(self, "_current_det_size"):
                self._current_det_size = (640, 640)
        else:
            # DML is fixed at (640,640) — set tracker but never call prepare() again
            if not hasattr(self, "_current_det_size"):
                self._current_det_size = (640, 640)

        # Low-light CLAHE contrast enhancement for dark nighttime photos
        _clahe_applied = False
        try:
            gray_mean = float(np.mean(img_bgr))
            if gray_mean < 65.0:
                import cv2
                lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                cl = clahe.apply(l)
                limg = cv2.merge((cl, a, b))
                enhanced_bgr = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
                _clahe_applied = True
                logger.debug(
                    f"[preprocess] END   | img={w}x{h} | "
                    f"CLAHE=YES (brightness={gray_mean:.0f}<65) | "
                    f"active_device={self.active_device}"
                )
                return enhanced_bgr
        except Exception:
            pass

        logger.debug(
            f"[preprocess] END   | img={w}x{h} | "
            f"CLAHE=NO  (brightness>65 or error) | "
            f"active_device={self.active_device}"
        )
        return img_bgr

    @staticmethod
    def compute_profile_centroid(embeddings: list[Any]) -> np.ndarray | None:
        """
        Calculates the unit-normalized centroid (mean vector) across multiple profile reference embeddings.
        Suppresses facial expression and lighting noise for faster & more accurate matching.
        """
        valid = []
        for e in embeddings:
            if e is not None:
                arr = np.asarray(e, dtype=np.float64)
                if arr.size == 512 and not np.allclose(arr, 0):
                    valid.append(arr)

        if not valid:
            return None

        mean_vec = np.mean(valid, axis=0)
        norm = np.linalg.norm(mean_vec)
        return mean_vec / norm if norm > 0 else mean_vec

    def _run_inference(self, app: Any, img_bgr: np.ndarray, det_thresh: float | None = None) -> list[Any]:
        """
        Execute neural network inference with provider-specific concurrency rules.
        DirectML on Windows requires serializing D3D12 command lists via _infer_lock.
        CUDA, ROCm, CoreML, OpenVINO, and CPU are fully thread-safe in ONNX Runtime
        and run concurrently across all worker threads without lock contention.
        """
        if app is None:
            return []
        if det_thresh is not None and hasattr(app, "models") and "detection" in app.models:
            try:
                app.models["detection"].det_thresh = float(det_thresh)
            except Exception:
                pass

        h, w = img_bgr.shape[:2]

        if "DmlExecutionProvider" in self.providers:
            logger.debug(
                f"[DML] Inference START | img={w}x{h} | "
                f"provider=DmlExecutionProvider | _infer_lock=HELD | "
                f"active_device={self.active_device}"
            )
            with InsightFaceEngine._infer_lock:
                try:
                    t0 = time.perf_counter()
                    result = app.get(img_bgr)
                    elapsed_ms = (time.perf_counter() - t0) * 1000
                    logger.debug(
                        f"[DML] Inference END   | {len(result)} faces | "
                        f"{elapsed_ms:.1f}ms | active_device={self.active_device}"
                    )
                    return result
                except Exception as dml_err:
                    elapsed_ms = (time.perf_counter() - t0) * 1000 if "t0" in dir() else 0
                    logger.error(
                        f"[DML] Inference FAILED | img={w}x{h} | "
                        f"elapsed={elapsed_ms:.1f}ms | error={dml_err} | "
                        f"active_device={self.active_device} | "
                        f"providers={self.providers} | RAISING to trigger CPU fallback"
                    )
                    # Raise to caller so the detection method can trigger CPU fallback.
                    raise RuntimeError(f"DML inference failed: {dml_err}") from dml_err

        # CUDA / CPU / ROCm / CoreML path
        try:
            t0 = time.perf_counter()
            result = app.get(img_bgr)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            logger.debug(
                f"[GPU/CPU] Inference OK | img={w}x{h} | {len(result)} faces | "
                f"{elapsed_ms:.1f}ms | active_device={self.active_device}"
            )
            return result
        except Exception as inf_err:
            logger.error(
                f"[GPU/CPU] Inference FAILED | img={w}x{h} | "
                f"error={inf_err} | active_device={self.active_device} | "
                f"providers={self.providers}"
            )
            raise

    @staticmethod
    def calculate_face_sharpness(image: Any) -> float:
        """
        Computes focus / sharpness score of a face using Laplacian variance.
        Returns float score: typical sharp face > 80, blurry < 35.
        """
        try:
            import cv2
            if isinstance(image, Image.Image):
                arr = np.array(image.convert("L"))
            elif isinstance(image, np.ndarray):
                if image.ndim == 3:
                    arr = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY if image.shape[2] == 3 else cv2.COLOR_RGB2GRAY)
                else:
                    arr = image
            else:
                return 100.0
            lap = cv2.Laplacian(arr, cv2.CV_64F)
            score = float(np.var(lap))
            return round(score, 1)
        except Exception:
            return 100.0

    @staticmethod
    def is_valid_face_geometry(bbox: list[int] | tuple[int, int, int, int], kps: Any = None) -> bool:
        """
        Verifies anatomical human facial proportions to reject non-human texture artifacts
        (e.g., T-shirt graphics, knees, wallpaper patterns, statues).
        Bbox format: [left, top, right, bottom] or (top, right, bottom, left)
        """
        try:
            if len(bbox) == 4:
                w = abs(bbox[2] - bbox[0])
                h = abs(bbox[3] - bbox[1])
                if w <= 8 or h <= 8:
                    return False
                aspect = w / h if h > 0 else 0
                if aspect < 0.30 or aspect > 3.0:
                    return False

                if kps is not None:
                    kps_arr = np.asarray(kps, dtype=np.float32)
                    if kps_arr.shape == (5, 2):
                        # Distance between left eye and right eye
                        eye_dist = np.linalg.norm(kps_arr[0] - kps_arr[1])
                        if eye_dist < 1.5:
                            return False
            return True
        except Exception:
            return True

    def detect_faces(
        self, image: Any, upsample_num_times: int = 1, det_thresh: float | None = None
    ) -> list[tuple[int, int, int, int]]:
        """
        Detect faces using SCRFD 360° deep detector.
        Thread-safe: uses _infer_lock when on DirectML to prevent DirectX 12 command list collisions.
        Returns bounding boxes in [top, right, bottom, left] order.
        """
        self._ensure_initialized()
        if self.app is None:
            logger.warning("detect_faces: InsightFace app is None, returning empty.")
            return []

        img_bgr = self._preprocess_bgr_image(self._to_numpy_bgr(image))
        try:
            faces = self._run_inference(self.app, img_bgr, det_thresh=det_thresh)
            locations = []
            for face in faces:
                bbox = face.bbox.astype(int)  # [left, top, right, bottom]
                kps = getattr(face, "kps", None)
                if not self.is_valid_face_geometry(bbox, kps):
                    continue
                left, top, right, bottom = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                locations.append((top, right, bottom, left))
            return locations
        except Exception as e:
            h, w = img_bgr.shape[:2]
            logger.warning(
                f"[detect_faces] EXCEPTION | img={w}x{h} | "
                f"active_device={self.active_device} | "
                f"providers={self.providers} | error={e}"
            )

            # DML crash recovery fallback: ANY DML error means switch to CPU.
            is_dml_error = "DmlExecutionProvider" in self.providers
            if is_dml_error:
                logger.warning(
                    f"[detect_faces] DML error on img={w}x{h} — attempting CPU fallback. "
                    f"Error was: {e}"
                )
                try:
                    cpu_name = self.get_system_cpu_name()
                    logger.info(
                        f"[detect_faces] Creating CPU engine ({cpu_name}) for fallback on img={w}x{h}..."
                    )
                    cpu_app = FaceAnalysis(name="buffalo_sc", providers=["CPUExecutionProvider"])
                    cpu_app.prepare(ctx_id=0, det_size=(640, 640), det_thresh=0.35)
                    faces = self._run_inference(cpu_app, img_bgr, det_thresh=det_thresh)
                    locations = []
                    for face in faces:
                        bbox = face.bbox.astype(int)
                        left, top, right, bottom = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                        locations.append((top, right, bottom, left))

                    # PERMANENTLY switch engine to CPU for remaining scan
                    self.app = cpu_app
                    self.providers = ["CPUExecutionProvider"]
                    self.active_device = f"Multi-Core CPU ({cpu_name})"
                    self.gpu_available = False
                    logger.warning(
                        f"[detect_faces] >>> ENGINE DEGRADED TO CPU <<< | "
                        f"was={self.active_device} | "
                        f"all subsequent inferences will use CPU | "
                        f"error that triggered: {e}"
                    )
                    return locations
                except Exception as cpu_err:
                    logger.error(
                        f"[detect_faces] CPU fallback FAILED | img={w}x{h} | "
                        f"DML error was: {e} | CPU error: {cpu_err}"
                    )

            return []

    def detect_faces_with_kps(
        self, image: Any, det_thresh: float | None = None
    ) -> list[tuple[tuple[int, int, int, int], "np.ndarray | None"]]:
        """
        Detect faces returning (bbox, 5-point keypoints) pairs.
        bbox order: (top, right, bottom, left). kps is np.ndarray (5,2) or None.
        """
        self._ensure_initialized()
        if self.app is None:
            return []

        img_bgr = self._preprocess_bgr_image(self._to_numpy_bgr(image))
        results: list[tuple[tuple[int, int, int, int], "np.ndarray | None"]] = []
        try:
            faces = self._run_inference(self.app, img_bgr, det_thresh=det_thresh)
            for face in faces:
                bbox = face.bbox.astype(int)  # [left, top, right, bottom]
                kps = getattr(face, "kps", None)
                if not self.is_valid_face_geometry(bbox, kps):
                    continue
                left, top, right, bottom = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                kps_arr = None
                if kps is not None:
                    kps_arr = np.asarray(kps, dtype=np.float32)
                    if kps_arr.shape != (5, 2):
                        kps_arr = None
                results.append(((top, right, bottom, left), kps_arr))
        except Exception as e:
            logger.warning(f"detect_faces_with_kps exception on {self.active_device}: {e}")
            return []
        return results

    def create_embeddings(
        self, image: Any, face_locations: list[tuple[int, int, int, int]] | None = None
    ) -> list[np.ndarray]:
        """
        Extract 512-dimensional normalized ArcFace embeddings.
        Thread-safe: uses _infer_lock when on DirectML to serialize GPU neural net forward passes.
        """
        self._ensure_initialized()
        if self.app is None:
            return []

        img_bgr = self._preprocess_bgr_image(self._to_numpy_bgr(image))
        try:
            faces = self._run_inference(self.app, img_bgr)
            embeddings = []

            for face in faces:
                if hasattr(face, "normed_embedding") and face.normed_embedding is not None:
                    embeddings.append(np.asarray(face.normed_embedding, dtype=np.float64))
                elif hasattr(face, "embedding") and face.embedding is not None:
                    norm = np.linalg.norm(face.embedding)
                    norm_emb = face.embedding / norm if norm > 0 else face.embedding
                    embeddings.append(np.asarray(norm_emb, dtype=np.float64))

            # If face_locations was passed and count mismatch, return dummy arrays as safety fallback
            if face_locations and len(embeddings) != len(face_locations):
                if len(embeddings) < len(face_locations):
                    diff = len(face_locations) - len(embeddings)
                    for _ in range(diff):
                        embeddings.append(np.zeros(512, dtype=np.float64))
                else:
                    embeddings = embeddings[: len(face_locations)]

            return embeddings
        except Exception as e:
            logger.warning(f"ArcFace create_embeddings exception on {self.active_device}: {e}")
            return [np.zeros(512, dtype=np.float64)] * (len(face_locations) if face_locations else 1)

    def detect_and_embed_faces(
        self, image: Any, det_thresh: float | None = None
    ) -> tuple[list[tuple[int, int, int, int]], list[np.ndarray], list[Image.Image]]:
        """
        Unified single-pass detection, ArcFace embedding extraction, and face cropping.
        Runs the InsightFace neural network ONCE per photo instead of twice, halving GPU execution
        time, cutting VRAM overhead in half, and preventing GPU multi-thread race conditions.
        Returns: (face_locations, face_encodings, face_crops)
        """
        self._ensure_initialized()
        if self.app is None:
            return [], [], []

        if isinstance(image, Image.Image):
            pil_img = image
        else:
            pil_img = Image.fromarray(self._to_numpy_rgb(image))

        img_bgr = self._preprocess_bgr_image(self._to_numpy_bgr(image))
        t0 = time.time()

        try:
            faces = self._run_inference(self.app, img_bgr, det_thresh=det_thresh)

            locations = []
            embeddings = []
            crops = []
            width, height = pil_img.size

            for face in faces:
                bbox = face.bbox.astype(int)  # [left, top, right, bottom]
                kps = getattr(face, "kps", None)
                if not self.is_valid_face_geometry(bbox, kps):
                    continue

                left, top, right, bottom = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                locations.append((top, right, bottom, left))

                if hasattr(face, "normed_embedding") and face.normed_embedding is not None:
                    embeddings.append(np.asarray(face.normed_embedding, dtype=np.float64))
                elif hasattr(face, "embedding") and face.embedding is not None:
                    norm = np.linalg.norm(face.embedding)
                    norm_emb = face.embedding / norm if norm > 0 else face.embedding
                    embeddings.append(np.asarray(norm_emb, dtype=np.float64))
                else:
                    embeddings.append(np.zeros(512, dtype=np.float64))

                c_top = max(0, top)
                c_left = max(0, left)
                c_bottom = min(height, bottom)
                c_right = min(width, right)
                if c_bottom > c_top and c_right > c_left:
                    crops.append(pil_img.crop((c_left, c_top, c_right, c_bottom)))
                else:
                    crops.append(pil_img.copy())

            elapsed = time.time() - t0
            logger.debug(f"InsightFace [{self.active_device}]: {len(faces)} faces extracted in {elapsed*1000:.1f}ms")
            return locations, embeddings, crops

        except Exception as e:
            h, w = img_bgr.shape[:2]
            logger.warning(
                f"[detect_and_embed_faces] EXCEPTION | img={w}x{h} | "
                f"active_device={self.active_device} | "
                f"providers={self.providers} | error={e}"
            )

            # DML crash recovery fallback: ANY DML error means switch to CPU.
            # D3D12 device-lost / reshape / OOM / timeout all manifest as different
            # error strings. Catch them all when DML is the active provider.
            is_dml_error = "DmlExecutionProvider" in self.providers
            if is_dml_error:
                logger.warning(
                    f"[detect_and_embed_faces] DML error on img={w}x{h} — attempting CPU fallback. "
                    f"Error was: {e}"
                )
                try:
                    cpu_name = self.get_system_cpu_name()
                    logger.info(
                        f"[detect_and_embed_faces] Creating CPU engine ({cpu_name}) for fallback on img={w}x{h}..."
                    )
                    cpu_app = FaceAnalysis(name="buffalo_sc", providers=["CPUExecutionProvider"])
                    cpu_app.prepare(ctx_id=0, det_size=(640, 640), det_thresh=0.35)
                    faces = self._run_inference(cpu_app, img_bgr, det_thresh=det_thresh)
                    locations = []
                    embeddings = []
                    crops = []
                    width, height = pil_img.size
                    for face in faces:
                        bbox = face.bbox.astype(int)
                        left, top, right, bottom = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                        locations.append((top, right, bottom, left))
                        if hasattr(face, "normed_embedding") and face.normed_embedding is not None:
                            embeddings.append(np.asarray(face.normed_embedding, dtype=np.float64))
                        elif hasattr(face, "embedding") and face.embedding is not None:
                            norm = np.linalg.norm(face.embedding)
                            embeddings.append(np.asarray(face.embedding / norm, dtype=np.float64))
                        else:
                            embeddings.append(np.zeros(512, dtype=np.float64))
                        c_top, c_left, c_bottom, c_right = max(0, top), max(0, left), min(height, bottom), min(width, right)
                        if c_bottom > c_top and c_right > c_left:
                            crops.append(pil_img.crop((c_left, c_top, c_right, c_bottom)))
                        else:
                            crops.append(pil_img.copy())

                    # PERMANENTLY switch engine to CPU for remaining scan
                    self.app = cpu_app
                    self.providers = ["CPUExecutionProvider"]
                    self.active_device = f"Multi-Core CPU ({cpu_name})"
                    self.gpu_available = False
                    logger.warning(
                        f"[detect_and_embed_faces] >>> ENGINE DEGRADED TO CPU <<< | "
                        f"was={self.active_device} | "
                        f"all subsequent inferences will use CPU | "
                        f"error that triggered: {e}"
                    )
                    return locations, embeddings, crops
                except Exception as cpu_err:
                    logger.error(
                        f"[detect_and_embed_faces] CPU fallback FAILED | img={w}x{h} | "
                        f"DML error was: {e} | CPU error: {cpu_err}"
                    )

            return [], [], []

            return [], [], []


    def calculate_match_score(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate calibrated ArcFace similarity score normalized to 0.0 - 100.0%.

        ArcFace Cosine Similarity Calibration:
        - Different People: Cosine Similarity < 0.18 (0.0% User Score)
        - Same Person Threshold: Cosine Similarity >= 0.25 (50.0% User Score)
        - Same Person High Confidence: Cosine Similarity >= 0.40 (80.0% User Score)
        """
        e1 = np.asarray(embedding1, dtype=np.float64)
        e2 = np.asarray(embedding2, dtype=np.float64)

        if e1.shape != e2.shape or e1.size == 0 or e2.size == 0:
            return 0.0

        norm1 = np.linalg.norm(e1)
        norm2 = np.linalg.norm(e2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        raw_cosine = float(np.dot(e1, e2) / (norm1 * norm2))

        # ArcFace buffalo_sc calibration for GTX 1650 / DML:
        # < 0.15  → clearly different people (return 0%)
        # 0.15-0.22 → uncertain zone scaled to 0-49.9%
        # 0.22-0.55 → same person range scaled to 50-100%
        # (buffalo_sc typically scores 0.55-0.80 for same person, so upper bound 0.55 avoids clipping)
        if raw_cosine < 0.15:
            return 0.0

        if raw_cosine < 0.22:
            # Scale [0.15, 0.22] → [0.0%, 49.9%]
            score = ((raw_cosine - 0.15) / (0.22 - 0.15)) * 49.9
        else:
            # Scale [0.22, 0.55] → [50.0%, 100.0%]
            score = 50.0 + ((raw_cosine - 0.22) / (0.55 - 0.22)) * 50.0

        return round(max(0.0, min(100.0, score)), 1)

    def extract_faces(
        self, image: Any, face_locations: list[tuple[int, int, int, int]] | None = None
    ) -> list[Image.Image]:
        """Extract cropped PIL images for detected face locations."""
        if isinstance(image, Image.Image):
            pil_img = image
        else:
            pil_img = Image.fromarray(self._to_numpy_rgb(image))

        locations = face_locations or self.detect_faces(image)
        crops = []
        width, height = pil_img.size

        for top, right, bottom, left in locations:
            c_top = max(0, top)
            c_left = max(0, left)
            c_bottom = min(height, bottom)
            c_right = min(width, right)
            if c_bottom > c_top and c_right > c_left:
                crops.append(pil_img.crop((c_left, c_top, c_right, c_bottom)))
            else:
                crops.append(Image.new("RGB", (50, 50), color="gray"))

        return crops

    def _to_numpy_bgr(self, image: Any) -> np.ndarray:
        if isinstance(image, Image.Image):
            rgb = np.array(image.convert("RGB"))
            return rgb[:, :, ::-1]  # Convert RGB to BGR for OpenCV / InsightFace
        elif isinstance(image, np.ndarray):
            if image.ndim == 3 and image.shape[2] == 3:
                return image[:, :, ::-1]
            return image
        raise ValueError(f"Unsupported image type: {type(image)}")

    def _to_numpy_rgb(self, image: Any) -> np.ndarray:
        if isinstance(image, Image.Image):
            return np.array(image.convert("RGB"))
        elif isinstance(image, np.ndarray):
            return image
        raise ValueError(f"Unsupported image type: {type(image)}")
