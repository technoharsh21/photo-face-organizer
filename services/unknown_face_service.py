"""
Unknown Face Service Module.

Manages unmatched faces detected during scans.
Stores crop, encoding, source photo info, and scan ID locally.
Clusters similar unknown faces into groups.
Allows renaming groups, deleting individual unknown faces, or converting unknown groups into new Profiles.
"""

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from config import Config
from domain.calibration import calibrate_match_score
from services.profile_service import ProfileService

logger = logging.getLogger(__name__)


class UnknownFaceService:
    """Manages storage, clustering, viewing, and converting of unknown (unmatched) faces."""

    def __init__(self, config: Config, profile_service: ProfileService):
        self.config = config
        self.profile_service = profile_service
        self.unknown_dir = config.unknown_faces_dir
        self.unknown_dir.mkdir(parents=True, exist_ok=True)
        self._profiles_cache: list[tuple[str, list[np.ndarray]]] = []
        self._profiles_cache_time: float = 0.0

    def _get_profile_embeddings_cache(self) -> list[tuple[str, list[np.ndarray]]]:
        """Fetch and cache pre-converted numpy arrays for all profiles in the system (refreshed every 5s)."""
        now = time.time()
        if self._profiles_cache and (now - self._profiles_cache_time) < 5.0:
            return self._profiles_cache

        cache = []
        for p in self.profile_service.list_profiles():
            name = p.get("name", "Unknown")
            embs = [np.asarray(e, dtype=np.float64) for e in p.get("embeddings", []) if len(e) > 0]
            if embs:
                cache.append((name, embs))

        self._profiles_cache = cache
        self._profiles_cache_time = now
        return cache

    def is_known_profile_face(self, face_encoding: np.ndarray, threshold: float = 50.0) -> bool:
        """
        Check if face_encoding matches ANY existing profile in the system.
        Prevents faces belonging to existing profiles from cluttering Unknown Faces.
        """
        if face_encoding is None or face_encoding.size == 0 or np.allclose(face_encoding, 0):
            return False

        profiles_cache = self._get_profile_embeddings_cache()
        for p_name, embs in profiles_cache:
            for ref_arr in embs:
                if ref_arr.shape == face_encoding.shape:
                    score = self.profile_service.face_engine.calculate_match_score(face_encoding, ref_arr)
                    if score >= threshold:
                        logger.info(f"Face matches existing profile '{p_name}' ({score:.1f}%). Skipping unknown face registration.")
                        return True
        return False

    def store_unknown_face(
        self,
        face_crop: Image.Image,
        face_encoding: np.ndarray,
        source_photo_path: str,
        bounding_box: list[int],
        scan_id: str,
        check_existing_profiles: bool = True,
    ) -> dict[str, Any] | None:
        """
        Save cropped image, encoding, and metadata for an unknown face.
        Returns None if face belongs to an existing profile in the system.
        """
        if check_existing_profiles and self.is_known_profile_face(face_encoding):
            return None

        u_id = str(uuid.uuid4())
        u_dir = self.unknown_dir / u_id
        u_dir.mkdir(parents=True, exist_ok=True)

        crop_path = u_dir / "crop.jpg"
        face_crop.save(crop_path, format="JPEG", quality=90)

        metadata = {
            "id": u_id,
            "scan_id": scan_id,
            "source_photo_path": source_photo_path,
            "bounding_box": list(bounding_box),
            "group_id": None,  # Will be assigned during clustering/grouping
            "crop_path": str(crop_path),
            "created_at": str(np.datetime64("now")),
        }

        with open(u_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        np.save(str(u_dir / "embedding.npy"), face_encoding)

        return metadata

    def list_unknown_faces(self) -> list[dict[str, Any]]:
        """Return list of all stored unknown face metadata."""
        unknowns = []
        for u_dir in self.unknown_dir.iterdir():
            if u_dir.is_dir():
                meta_path = u_dir / "metadata.json"
                emb_path = u_dir / "embedding.npy"
                if meta_path.exists() and emb_path.exists():
                    try:
                        with open(meta_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                        meta["embedding"] = np.load(str(emb_path))
                        unknowns.append(meta)
                    except Exception:
                        pass
        return unknowns

    def group_unknown_faces(self, threshold: float = 80.0) -> list[dict[str, Any]]:
        """
        Clusters unknown faces with high precision (default 80%+ similarity threshold).
        Enforces 100% group purity by requiring candidate faces to match ALL existing member faces in a group.
        Returns list of groups: [{'group_id': ..., 'group_name': ..., 'faces': [...]}]
        """
        all_faces = self.list_unknown_faces()
        if not all_faces:
            return []

        groups: list[dict[str, Any]] = []
        visited = set()

        for face in all_faces:
            f_id = face["id"]
            if f_id in visited:
                continue

            # Start new group
            group_id = face.get("group_id") or f"group_{uuid.uuid4().hex[:8]}"
            group_name = face.get("group_name") or f"Unknown Person ({len(groups) + 1})"
            group_faces = [face]
            visited.add(f_id)

            for other in all_faces:
                o_id = other["id"]
                if o_id in visited:
                    continue

                o_emb = other["embedding"]

                # Purity Check: Candidate 'other' face must score >= 80% against ALL existing members in this group
                matches_all_members = True
                for member in group_faces:
                    m_emb = member["embedding"]
                    if m_emb.shape != o_emb.shape:
                        matches_all_members = False
                        break

                    score = self.profile_service.face_engine.calculate_match_score(m_emb, o_emb)
                    if score < threshold:
                        matches_all_members = False
                        break

                if matches_all_members:
                    group_faces.append(other)
                    visited.add(o_id)

            # Update metadata on disk with group_id and group_name
            for gf in group_faces:
                gf["group_id"] = group_id
                gf["group_name"] = group_name
                self._update_metadata(gf)

            groups.append({
                "group_id": group_id,
                "group_name": group_name,
                "faces": group_faces
            })

        return groups

    def rename_group(self, group_id: str, new_name: str):
        """Rename an unknown face group."""
        all_faces = self.list_unknown_faces()
        for face in all_faces:
            if face.get("group_id") == group_id:
                face["group_name"] = new_name
                self._update_metadata(face)

    def convert_group_to_profile(self, group_id: str, profile_name: str) -> dict[str, Any] | None:
        """
        Creates a new Profile with profile_name, adds unknown face crops/embeddings as reference photos,
        and removes the converted unknown faces from storage.
        """
        all_faces = self.list_unknown_faces()
        group_faces = [f for f in all_faces if f.get("group_id") == group_id]

        if not group_faces:
            return None

        # 1. Create new profile
        profile = self.profile_service.create_profile(profile_name)

        # 2. Add each unknown face as a reference photo directly using its pre-computed embedding
        for gf in group_faces:
            crop_path = Path(gf["crop_path"])
            emb = gf.get("embedding")
            u_id = gf["id"]

            if emb is None:
                emb_path = self.unknown_dir / u_id / "embedding.npy"
                if emb_path.exists():
                    emb = np.load(str(emb_path))

            if crop_path.exists() and emb is not None:
                success, _ = self.profile_service.add_reference_photo_direct(
                    profile_id=profile["id"],
                    image_path=crop_path,
                    embedding=emb,
                )
                if success:
                    self.delete_unknown_face(u_id)

        return self.profile_service.get_profile(profile["id"])

    def add_group_to_existing_profile(self, group_id: str, profile_id: str) -> dict[str, Any] | None:
        """
        Appends unknown face crops from a group as reference photos to an existing Profile (profile_id),
        and removes the transferred unknown faces from storage.
        """
        all_faces = self.list_unknown_faces()
        group_faces = [f for f in all_faces if f.get("group_id") == group_id]

        if not group_faces:
            return None

        for gf in group_faces:
            crop_path = Path(gf["crop_path"])
            emb = gf.get("embedding")
            u_id = gf["id"]

            if emb is None:
                emb_path = self.unknown_dir / u_id / "embedding.npy"
                if emb_path.exists():
                    emb = np.load(str(emb_path))

            if crop_path.exists() and emb is not None:
                success, _ = self.profile_service.add_reference_photo_direct(
                    profile_id=profile_id,
                    image_path=crop_path,
                    embedding=emb,
                )
                if success:
                    self.delete_unknown_face(u_id)

        return self.profile_service.get_profile(profile_id)

    def delete_unknown_face(self, unknown_id: str) -> bool:
        """Remove single unknown face directory."""
        u_dir = self.unknown_dir / unknown_id
        if u_dir.exists():
            import shutil
            shutil.rmtree(u_dir)
            return True
        return False

    def delete_group(self, group_id: str) -> int:
        """Delete all unknown faces belonging to group_id."""
        all_faces = self.list_unknown_faces()
        group_faces = [f for f in all_faces if f.get("group_id") == group_id]
        deleted_count = 0
        for gf in group_faces:
            if self.delete_unknown_face(gf["id"]):
                deleted_count += 1
        return deleted_count

    def _update_metadata(self, face: dict[str, Any]):
        """Persist metadata to disk (excluding embedding numpy array)."""
        u_id = face["id"]
        u_dir = self.unknown_dir / u_id
        if u_dir.exists():
            meta = {k: v for k, v in face.items() if k != "embedding"}
            with open(u_dir / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
