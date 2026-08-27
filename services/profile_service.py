"""
Profile Service.

Manages face profiles, reference images, face encodings, and bulk profile operations.
Copies reference photos to application storage without altering original files.
Supports selecting specific face from multi-face group reference photos.
"""

import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from PIL import Image

from config import Config
from domain.face_engine import FaceEngine
from domain.image_loader import load_image


class ProfileService:
    """Manages creation, editing, reference photos, encodings, and deletion of profiles."""

    def __init__(self, config: Config, face_engine: FaceEngine):
        self.config = config
        self.face_engine = face_engine
        self.profiles_dir = config.profiles_dir
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def _normalize_profile_data(self, data: dict[str, Any], p_dir: Path) -> dict[str, Any]:
        """Normalize profile data dictionary for backwards compatibility with legacy formats."""
        if "references" not in data:
            data["references"] = []
            # Check for legacy reference_images
            legacy_refs = data.get("reference_images", [])
            for ref in legacy_refs:
                fname = ref.get("filename", "")
                ref_path = p_dir / "reference_images" / fname
                if ref_path.exists():
                    data["references"].append({
                        "id": ref.get("name", str(uuid.uuid4())),
                        "filename": fname,
                        "bbox": [0, 0, 0, 0],
                        "stored_path": str(ref_path),
                    })

        if "embeddings" not in data:
            data["embeddings"] = []
            # Check for legacy embedding json files
            emb_file = self.profiles_dir / "embeddings" / f"{data.get('id')}.json"
            if emb_file.exists():
                try:
                    with open(emb_file, "r", encoding="utf-8") as f:
                        data["embeddings"] = json.load(f)
                except Exception:
                    pass

        return data

    def list_profiles(self) -> list[dict[str, Any]]:
        """Return list of all profile metadata dicts."""
        profiles = []
        for p_dir in self.profiles_dir.iterdir():
            if p_dir.is_dir():
                p_file = p_dir / "profile.json"
                if p_file.exists():
                    try:
                        with open(p_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            normalized = self._normalize_profile_data(data, p_dir)
                            profiles.append(normalized)
                    except Exception:
                        pass
        # Sort profiles alphabetically by name
        profiles.sort(key=lambda x: x.get("name", "").lower())
        return profiles

    def get_profile(self, profile_id: str) -> dict[str, Any] | None:
        """Fetch profile by ID."""
        p_dir = self.profiles_dir / profile_id
        p_file = p_dir / "profile.json"
        if p_file.exists():
            try:
                with open(p_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return self._normalize_profile_data(data, p_dir)
            except Exception:
                return None
        return None

    def create_profile(
        self,
        name: str,
        notes: str = "",
        is_group_profile: bool = False,
        compulsory_profile_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new profile."""
        p_id = str(uuid.uuid4())
        p_dir = self.profiles_dir / p_id
        p_dir.mkdir(parents=True, exist_ok=True)
        (p_dir / "references").mkdir(exist_ok=True)
        (p_dir / "embeddings").mkdir(exist_ok=True)

        profile_data = {
            "id": p_id,
            "name": name.strip(),
            "notes": notes.strip(),
            "is_group_profile": is_group_profile,
            "compulsory_profile_ids": compulsory_profile_ids or [],
            "references": [],  # List of dicts: {'id': ref_id, 'filename': ..., 'bbox': ...}
            "embeddings": [],   # List of 128-d lists
        }

        self._save_profile(profile_data)
        return profile_data

    def rename_profile(self, profile_id: str, new_name: str) -> dict[str, Any] | None:
        """Rename an existing profile."""
        profile = self.get_profile(profile_id)
        if profile:
            profile["name"] = new_name.strip()
            self._save_profile(profile)
            return profile
        return None

    def update_profile_type(
        self, profile_id: str, is_group_profile: bool, compulsory_profile_ids: list[str] | None = None
    ) -> dict[str, Any] | None:
        """Update group profile settings."""
        profile = self.get_profile(profile_id)
        if profile:
            profile["is_group_profile"] = is_group_profile
            profile["compulsory_profile_ids"] = compulsory_profile_ids or []
            self._save_profile(profile)
            return profile
        return None

    def delete_profile(self, profile_id: str) -> bool:
        """Delete profile directory and all its application-stored files."""
        p_dir = self.profiles_dir / profile_id
        if p_dir.exists():
            shutil.rmtree(p_dir)
            return True
        return False

    def detect_faces_in_reference(self, image_path: Path) -> tuple[Image.Image | None, list[tuple[int, int, int, int]], list[Image.Image]]:
        """
        Loads reference photo and returns (pil_image, face_locations, list_of_cropped_face_images).
        """
        pil_img, err = load_image(image_path)
        if pil_img is None:
            return None, [], []

        locations = self.face_engine.detect_faces(pil_img)
        crops = self.face_engine.extract_faces(pil_img, locations)
        return pil_img, locations, crops

    def add_reference_photo(
        self,
        profile_id: str,
        image_path: Path,
        selected_face_index: int | None = None
    ) -> tuple[bool, str]:
        """
        Adds a reference photo to profile.
        If image contains multiple faces and selected_face_index is None,
        returns (False, "MULTIPLE_FACES_DETECTED").
        If selected_face_index is provided or exactly 1 face exists, processes face encoding and saves reference copy.
        """
        profile = self.get_profile(profile_id)
        if not profile:
            return False, "Profile not found"

        pil_img, locations, crops = self.detect_faces_in_reference(image_path)
        if pil_img is None:
            return False, "Could not load reference image"

        if len(locations) == 0:
            return False, "No face detected in reference photo"

        if len(locations) > 1 and selected_face_index is None:
            return False, "MULTIPLE_FACES"

        idx = selected_face_index if selected_face_index is not None else 0
        if idx < 0 or idx >= len(locations):
            return False, "Invalid face selection index"

        target_bbox = [locations[idx]] # List with single bbox
        encodings = self.face_engine.create_embeddings(pil_img, target_bbox)

        if not encodings:
            return False, "Failed to generate face encoding"

        encoding = encodings[0]

        # Copy reference photo into profile's storage
        ref_id = str(uuid.uuid4())
        ref_filename = f"ref_{ref_id}{image_path.suffix.lower()}"
        ref_dest_dir = self.profiles_dir / profile_id / "references"
        ref_dest_dir.mkdir(parents=True, exist_ok=True)
        ref_dest_path = ref_dest_dir / ref_filename

        # Save copied reference
        pil_img.save(ref_dest_path)

        # Record metadata & encoding
        ref_entry = {
            "id": ref_id,
            "filename": ref_filename,
            "bbox": list(locations[idx]),
            "stored_path": str(ref_dest_path),
        }
        profile.setdefault("references", []).append(ref_entry)
        profile.setdefault("embeddings", []).append(encoding.tolist())

        self._save_profile(profile)
        return True, "Reference photo added successfully"

    def remove_reference_photo(self, profile_id: str, ref_id: str) -> bool:
        """Remove reference photo and its associated encoding from profile."""
        profile = self.get_profile(profile_id)
        if not profile:
            return False

        ref_index = -1
        for i, ref in enumerate(profile.get("references", [])):
            if ref.get("id") == ref_id:
                ref_index = i
                break

        if ref_index >= 0:
            ref_entry = profile["references"].pop(ref_index)
            if ref_index < len(profile.get("embeddings", [])):
                profile["embeddings"].pop(ref_index)

            # Delete file if exists
            stored_path = ref_entry.get("stored_path")
            if stored_path and Path(stored_path).exists():
                try:
                    Path(stored_path).unlink()
                except Exception:
                    pass

            self._save_profile(profile)
            return True
        return False

    def bulk_import_profiles(self, folder_path: Path) -> list[dict[str, Any]]:
        """
        Imports folders where subfolder name is person name and images inside are reference images.
        """
        imported = []
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            return imported

        for subfolder in folder.iterdir():
            if subfolder.is_dir():
                person_name = subfolder.name
                profile = self.create_profile(person_name)
                for img_file in subfolder.iterdir():
                    if img_file.is_file():
                        # Try adding reference
                        pil_img, locations, crops = self.detect_faces_in_reference(img_file)
                        if len(locations) == 1:
                            self.add_reference_photo(profile["id"], img_file, selected_face_index=0)
                imported.append(self.get_profile(profile["id"]))
        return imported

    def _save_profile(self, profile_data: dict[str, Any]):
        """Save profile data to JSON file."""
        p_dir = self.profiles_dir / profile_data["id"]
        p_dir.mkdir(parents=True, exist_ok=True)
        p_file = p_dir / "profile.json"
        with open(p_file, "w", encoding="utf-8") as f:
            json.dump(profile_data, f, indent=2)
