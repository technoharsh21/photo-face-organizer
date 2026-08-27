"""
Unknown Face Service Module.

Manages unmatched faces detected during scans.
Stores crop, encoding, source photo info, and scan ID locally.
Clusters similar unknown faces into groups.
Allows renaming groups, deleting individual unknown faces, or converting unknown groups into new Profiles.
"""

import json
import uuid
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from config import Config
from domain.calibration import calibrate_match_score
from services.profile_service import ProfileService


class UnknownFaceService:
    """Manages storage, clustering, viewing, and converting of unknown (unmatched) faces."""

    def __init__(self, config: Config, profile_service: ProfileService):
        self.config = config
        self.profile_service = profile_service
        self.unknown_dir = config.unknown_faces_dir
        self.unknown_dir.mkdir(parents=True, exist_ok=True)

    def store_unknown_face(
        self,
        face_crop: Image.Image,
        face_encoding: np.ndarray,
        source_photo_path: str,
        bounding_box: list[int],
        scan_id: str,
    ) -> dict[str, Any]:
        """Save cropped image, encoding, and metadata for an unknown face."""
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

    def group_unknown_faces(self, threshold: float = 50.0) -> list[dict[str, Any]]:
        """
        Clusters unknown faces using greedy distance thresholding.
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

            ref_emb = face["embedding"]

            for other in all_faces:
                o_id = other["id"]
                if o_id in visited:
                    continue

                o_emb = other["embedding"]
                dist = float(np.linalg.norm(ref_emb - o_emb))
                score = calibrate_match_score(dist)

                if score >= threshold:
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

        # 2. Add each unknown face as a reference photo
        for gf in group_faces:
            crop_path = Path(gf["crop_path"])
            if crop_path.exists():
                self.profile_service.add_reference_photo(
                    profile_id=profile["id"],
                    image_path=crop_path,
                    selected_face_index=0
                )
            # Delete unknown face record
            self.delete_unknown_face(gf["id"])

        return self.profile_service.get_profile(profile["id"])

    def delete_unknown_face(self, unknown_id: str) -> bool:
        """Remove single unknown face directory."""
        u_dir = self.unknown_dir / unknown_id
        if u_dir.exists():
            import shutil
            shutil.rmtree(u_dir)
            return True
        return False

    def _update_metadata(self, face: dict[str, Any]):
        """Persist metadata to disk (excluding embedding numpy array)."""
        u_id = face["id"]
        u_dir = self.unknown_dir / u_id
        if u_dir.exists():
            meta = {k: v for k, v in face.items() if k != "embedding"}
            with open(u_dir / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
