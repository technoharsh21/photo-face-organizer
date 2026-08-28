"""
Face Engine Abstraction and Implementation.

Decouples the rest of the application from the underlying face recognition library (ageitgey/face_recognition / dlib).
Supports CPU / GPU fallback, device querying, bounding box extraction, face cropping, embedding generation,
and calibrated match scoring.
"""

from abc import ABC, abstractmethod
from typing import Any

import numpy as np
from PIL import Image

from domain.calibration import calibrate_match_score


class FaceEngine(ABC):
    """Abstract base class defining the Face Engine contract."""

    @abstractmethod
    def detect_faces(self, image: Any, model: str = "hog") -> list[tuple[int, int, int, int]]:
        """
        Detect face bounding boxes in an image.
        Returns list of (top, right, bottom, left) tuples.
        """

    @abstractmethod
    def extract_faces(
        self, image: Any, face_locations: list[tuple[int, int, int, int]] | None = None
    ) -> list[Image.Image]:
        """
        Crop face regions from the image.
        """

    @abstractmethod
    def create_embeddings(
        self, image: Any, face_locations: list[tuple[int, int, int, int]] | None = None
    ) -> list[np.ndarray]:
        """
        Generate 128-dimensional encodings for face locations in the image.
        """

    @abstractmethod
    def compare_embeddings(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate Euclidean distance between two embeddings.
        """

    @abstractmethod
    def calculate_match_score(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate calibrated match score (0-100) between two embeddings.
        """

    @abstractmethod
    def set_device_preference(self, preference: str) -> str:
        """
        Set device preference ('Auto', 'CPU', 'GPU'). Returns active device ('CPU' or 'GPU').
        """

    @abstractmethod
    def get_device_info(self) -> dict[str, Any]:
        """
        Return device configuration and GPU availability status.
        """


class FaceRecognitionEngine(FaceEngine):
    """
    Concrete implementation of FaceEngine using ageitgey/face_recognition & dlib.
    """

    def __init__(self, device_preference: str = "Auto"):
        self._requested_device = device_preference
        self._gpu_available = False
        self._check_gpu_support()
        self._active_device = self._resolve_active_device(device_preference)
        self._model = "cnn" if self._active_device == "GPU" else "hog"

    def _check_gpu_support(self):
        try:
            import dlib
            self._gpu_available = bool(dlib.DLIB_USE_CUDA and dlib.cuda.get_num_devices() > 0)
        except Exception:
            self._gpu_available = False

    def _resolve_active_device(self, preference: str) -> str:
        if preference == "GPU":
            if self._gpu_available:
                return "GPU"
            else:
                # GPU requested but not available -> fallback to CPU
                return "CPU"
        elif preference == "Auto":
            return "GPU" if self._gpu_available else "CPU"
        else:
            return "CPU"

    def set_device_preference(self, preference: str) -> str:
        self._requested_device = preference
        self._active_device = self._resolve_active_device(preference)
        self._model = "cnn" if self._active_device == "GPU" else "hog"
        return self._active_device

    def get_device_info(self) -> dict[str, Any]:
        return {
            "requested_device": self._requested_device,
            "active_device": self._active_device,
            "gpu_available": self._gpu_available,
            "model_used": self._model
        }

    def _to_numpy_rgb(self, image: Any) -> np.ndarray:
        if isinstance(image, Image.Image):
            if image.mode != "RGB":
                image = image.convert("RGB")
            return np.array(image)
        elif isinstance(image, np.ndarray):
            return image
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")

    def detect_faces(self, image: Any, model: str | None = None, upsample_num_times: int = 1) -> list[tuple[int, int, int, int]]:
        import face_recognition
        rgb_img = self._to_numpy_rgb(image)
        use_model = model or self._model
        locations = face_recognition.face_locations(rgb_img, number_of_times_to_upsample=upsample_num_times, model=use_model)
        return locations

    def extract_faces(
        self, image: Any, face_locations: list[tuple[int, int, int, int]] | None = None
    ) -> list[Image.Image]:
        if isinstance(image, np.ndarray):
            pil_img = Image.fromarray(image)
        else:
            pil_img = image.convert("RGB")

        if face_locations is None:
            face_locations = self.detect_faces(pil_img)

        crops = []
        width, height = pil_img.size
        for (top, right, bottom, left) in face_locations:
            # Ensure boundaries are valid
            t = max(0, top)
            r = min(width, right)
            b = min(height, bottom)
            l = max(0, left)
            crop = pil_img.crop((l, t, r, b))
            crops.append(crop)
        return crops

    def create_embeddings(
        self, image: Any, face_locations: list[tuple[int, int, int, int]] | None = None
    ) -> list[np.ndarray]:
        import face_recognition
        rgb_img = self._to_numpy_rgb(image)
        if face_locations is None:
            face_locations = face_recognition.face_locations(rgb_img, model=self._model)
        encodings = face_recognition.face_encodings(rgb_img, known_face_locations=face_locations)
        return encodings

    def compare_embeddings(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        import face_recognition
        emb1 = np.asarray(embedding1, dtype=np.float64)
        emb2 = np.asarray(embedding2, dtype=np.float64)
        distances = face_recognition.face_distance([emb1], emb2)
        if len(distances) > 0:
            return float(distances[0])
        return 1.0

    def calculate_match_score(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        distance = self.compare_embeddings(embedding1, embedding2)
        return calibrate_match_score(distance)
