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
    def detect_faces(
        self, image: Any, model: str = "hog", det_thresh: float | None = None
    ) -> list[tuple[int, int, int, int]]:
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

    def detect_and_embed_faces(
        self, image: Any, det_thresh: float | None = None
    ) -> tuple[list[tuple[int, int, int, int]], list[np.ndarray], list[Image.Image]]:
        """
        Unified single-pass detection, ArcFace embedding extraction, and face cropping.
        Returns: (face_locations, face_encodings, face_crops)
        """
        locs = self.detect_faces(image, det_thresh=det_thresh)
        embs = self.create_embeddings(image, locs)
        crops = self.extract_faces(image, locs)
        return locs, embs, crops

    def detect_faces_with_kps(
        self, image: Any, det_thresh: float | None = None
    ) -> list[tuple[tuple[int, int, int, int], "np.ndarray | None"]]:
        """
        Detect faces returning (bbox, keypoints) pairs.
        Default implementation returns None keypoints; engines that expose
        landmark keypoints (e.g. InsightFace SCRFD) override this.
        bbox order: (top, right, bottom, left).
        """
        return [(loc, None) for loc in self.detect_faces(image, det_thresh=det_thresh)]


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


from domain.insight_engine import InsightFaceEngine, InsightFaceEngine as FaceRecognitionEngine
