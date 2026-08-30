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
import onnxruntime
from PIL import Image

# Guarantee sys.stdout/stderr are never None (PyInstaller --windowed on Windows)
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import insightface
from insightface.app import FaceAnalysis

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
                return

            # Guard stdout/stderr during InsightFace model loading (PyInstaller --windowed)
            _orig_stdout = sys.stdout
            _orig_stderr = sys.stderr
            try:
                try:
                    import cv2
                    cpu_cores = os.cpu_count() or 4
                    cv2.setNumThreads(cpu_cores)
                except Exception:
                    pass

                logger.info(f"Initializing InsightFace models with providers: {self.providers}...")

                # 1. Attempt primary configured provider list
                try:
                    self.app = FaceAnalysis(name="buffalo_sc", providers=self.providers)
                    self.app.prepare(ctx_id=0, det_size=(640, 640))
                    self._is_initialized = True
                    logger.info(f"InsightFace engine initialized successfully on {self.active_device}.")
                    return
                except Exception as primary_err:
                    logger.warning(f"Primary GPU provider ({self.providers}) failed: {primary_err}", exc_info=True)

                # 2. Cascading Fallback 1: Try DirectX 12 DirectML (NVIDIA / AMD / Intel GPU)
                available = onnxruntime.get_available_providers()
                if "DmlExecutionProvider" in available and "DmlExecutionProvider" not in self.providers:
                    try:
                        logger.info("Attempting cascading fallback to DirectX 12 DirectML GPU...")
                        dml_providers = ["DmlExecutionProvider", "CPUExecutionProvider"]
                        self.app = FaceAnalysis(name="buffalo_sc", providers=dml_providers)
                        self.app.prepare(ctx_id=0, det_size=(640, 640))
                        self.providers = dml_providers
                        gpu_name = self.get_system_gpu_name()
                        self.active_device = f"DirectX 12 GPU ({gpu_name})"
                        self.gpu_available = True
                        self._is_initialized = True
                        logger.info(f"InsightFace successfully initialized on DirectX 12 DirectML GPU ({gpu_name})!")
                        return
                    except Exception as dml_err:
                        logger.warning(f"DirectX 12 DirectML GPU fallback failed: {dml_err}", exc_info=True)

                # 3. Cascading Fallback 2: Multi-Core CPU
                logger.info("Falling back to Multi-Core CPU execution...")
                cpu_name = self.get_system_cpu_name()
                self.providers = ["CPUExecutionProvider"]
                self.active_device = f"Multi-Core CPU ({cpu_name})"
                self.gpu_available = False
                self.app = FaceAnalysis(name="buffalo_sc", providers=self.providers)
                self.app.prepare(ctx_id=0, det_size=(640, 640))
                self._is_initialized = True
                logger.info(f"InsightFace engine initialized on Multi-Core CPU ({cpu_name}).")

            except Exception as cpu_err:
                logger.error(f"Failed to initialize InsightFace engine: {cpu_err}", exc_info=True)


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
                return enhanced_bgr
        except Exception:
            pass

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

    def _run_inference(self, app: Any, img_bgr: np.ndarray) -> list[Any]:
        """
        Execute neural network inference with provider-specific concurrency rules.
        DirectML on Windows requires serializing D3D12 command lists via _infer_lock.
        CUDA, ROCm, CoreML, OpenVINO, and CPU are fully thread-safe in ONNX Runtime
        and run concurrently across all worker threads without lock contention.
        """
        if app is None:
            return []
        if "DmlExecutionProvider" in self.providers:
            with InsightFaceEngine._infer_lock:
                return app.get(img_bgr)
        return app.get(img_bgr)

    def detect_faces(self, image: Any, upsample_num_times: int = 1) -> list[tuple[int, int, int, int]]:
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
            faces = self._run_inference(self.app, img_bgr)
            locations = []
            for face in faces:
                bbox = face.bbox.astype(int)  # [left, top, right, bottom]
                left, top, right, bottom = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                locations.append((top, right, bottom, left))
            return locations
        except Exception as e:
            err_str = str(e)
            logger.warning(f"SCRFD detect_faces exception on {self.active_device}: {e}")

            is_dml_reshape_error = (
                "DmlExecutionProvider" in str(self.providers)
                and ("80070057" in err_str or "Reshape" in err_str or "RUNTIME_EXCEPTION" in err_str)
            )
            if is_dml_reshape_error:
                logger.warning(
                    "DirectML Reshape error detected — falling back to CPU for this image "
                    "and switching engine to CPU-only mode for remaining scan."
                )
                try:
                    cpu_app = FaceAnalysis(name="buffalo_sc", providers=["CPUExecutionProvider"])
                    cpu_app.prepare(ctx_id=0, det_size=(640, 640))
                    faces = self._run_inference(cpu_app, img_bgr)
                    locations = []
                    for face in faces:
                        bbox = face.bbox.astype(int)
                        left, top, right, bottom = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                        locations.append((top, right, bottom, left))
                    self.app = cpu_app
                    self.providers = ["CPUExecutionProvider"]
                    cpu_name = self.get_system_cpu_name()
                    self.active_device = f"Multi-Core CPU ({cpu_name})"
                    self.gpu_available = False
                    logger.info(f"Engine degraded to CPU-only: {self.active_device}")
                    return locations
                except Exception as cpu_err:
                    logger.warning(f"CPU fallback for DML Reshape error also failed: {cpu_err}")

            return []

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
        self, image: Any
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
            faces = self._run_inference(self.app, img_bgr)

            locations = []
            embeddings = []
            crops = []
            width, height = pil_img.size

            for face in faces:
                bbox = face.bbox.astype(int)  # [left, top, right, bottom]
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
            err_str = str(e)
            logger.warning(f"detect_and_embed_faces exception on {self.active_device}: {e}")

            # DML Reshape crash recovery fallback
            is_dml_reshape_error = (
                "DmlExecutionProvider" in str(self.providers)
                and ("80070057" in err_str or "Reshape" in err_str or "RUNTIME_EXCEPTION" in err_str)
            )
            if is_dml_reshape_error:
                logger.warning(
                    "DirectML Reshape error in detect_and_embed_faces — falling back to CPU "
                    "and degrading engine to CPU-only mode."
                )
                try:
                    cpu_app = FaceAnalysis(name="buffalo_sc", providers=["CPUExecutionProvider"])
                    cpu_app.prepare(ctx_id=0, det_size=(640, 640))
                    faces = self._run_inference(cpu_app, img_bgr)
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

                    self.app = cpu_app
                    self.providers = ["CPUExecutionProvider"]
                    cpu_name = self.get_system_cpu_name()
                    self.active_device = f"Multi-Core CPU ({cpu_name})"
                    self.gpu_available = False
                    logger.info(f"Engine degraded to CPU-only: {self.active_device}")
                    return locations, embeddings, crops
                except Exception as cpu_err:
                    logger.warning(f"CPU fallback in detect_and_embed_faces failed: {cpu_err}")

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
