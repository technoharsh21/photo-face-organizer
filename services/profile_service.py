"""
Profile Service.

Manages face profiles, reference images, face encodings, and bulk profile operations.
Copies reference photos to application storage without altering original files.
Supports selecting specific face from multi-face group reference photos and graceful fallback.
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

        for ref in data.get("references", []):
            if "stored_path" not in ref or not Path(ref["stored_path"]).exists():
                fname = ref.get("filename", "")
                alt_path = p_dir / "references" / fname
                if alt_path.exists():
                    ref["stored_path"] = str(alt_path)

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

        # Check embedding dimension compatibility (e.g. 128-d legacy vs 512-d ArcFace)
        need_reembed = False
        if data.get("references") and data.get("embeddings"):
            for emb in data["embeddings"]:
                if len(emb) != 512 and hasattr(self.face_engine, "app"):
                    need_reembed = True
                    break
        elif data.get("references") and not data.get("embeddings"):
            need_reembed = True

        if need_reembed:
            new_embs = []
            for ref in data.get("references", []):
                ref_path = Path(ref.get("stored_path", ""))
                if ref_path.exists():
                    pil_img, err = load_image(ref_path)
                    if pil_img is not None:
                        bbox = ref.get("bbox")
                        locs = [tuple(bbox)] if (bbox and len(bbox) == 4 and sum(bbox) > 0) else None
                        embs = self.face_engine.create_embeddings(pil_img, locs)
                        if embs:
                            new_embs.append(embs[0].tolist())
            if new_embs:
                data["embeddings"] = new_embs
                self._save_profile(data)

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
        """Create a new profile with name validation and duplicate name checking."""
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Profile name cannot be empty.")

        # Check duplicate profile name
        for p in self.list_profiles():
            if p.get("name", "").lower() == clean_name.lower():
                raise ValueError(f"A profile with name '{clean_name}' already exists.")

        p_id = str(uuid.uuid4())
        p_dir = self.profiles_dir / p_id
        p_dir.mkdir(parents=True, exist_ok=True)
        (p_dir / "references").mkdir(exist_ok=True)
        (p_dir / "embeddings").mkdir(exist_ok=True)

        profile_data = {
            "id": p_id,
            "name": clean_name,
            "notes": notes.strip(),
            "is_group_profile": is_group_profile,
            "compulsory_profile_ids": compulsory_profile_ids or [],
            "references": [],  # List of dicts: {'id': ref_id, 'filename': ..., 'bbox': ...}
            "embeddings": [],   # List of 128-d lists
        }

        self._save_profile(profile_data)
        return profile_data

    def rename_profile(self, profile_id: str, new_name: str) -> dict[str, Any] | None:
        """Rename an existing profile with duplicate checking."""
        clean_name = new_name.strip()
        if not clean_name:
            raise ValueError("Profile name cannot be empty.")

        for p in self.list_profiles():
            if p["id"] != profile_id and p.get("name", "").lower() == clean_name.lower():
                raise ValueError(f"A profile with name '{clean_name}' already exists.")

        profile = self.get_profile(profile_id)
        if profile:
            profile["name"] = clean_name
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
        selected_face_index: int | None = None,
        use_fallback_if_no_face: bool = False
    ) -> tuple[bool, str]:
        """
        Adds a reference photo to profile with strict validations:
        1. Face Must Be Detected (0 faces -> Error).
        2. Exactly 1 Face Allowed (2+ faces -> Error).
        3. Single Person Consistency Check (Must match existing profile reference photos >= 50% score).
        """
        import numpy as np

        profile = self.get_profile(profile_id)
        if not profile:
            return False, "Profile not found"

        pil_img, locations, crops = self.detect_faces_in_reference(image_path)
        if pil_img is None:
            return False, "Could not load reference image"

        # STRICT VALIDATION 1: Face Must Be Detected
        if len(locations) == 0:
            if use_fallback_if_no_face:
                width, height = pil_img.size
                locations = [(0, width, height, 0)]
            else:
                return False, "No face detected in reference photo. Please select a photo containing a clear human face."

        # STRICT VALIDATION 2: Exactly 1 Face Allowed
        if len(locations) > 1 and not profile.get("is_group_profile"):
            return False, f"Multiple faces ({len(locations)} faces) detected in this photo. Reference photos for a person profile must contain only 1 face."

        idx = selected_face_index if (selected_face_index is not None and selected_face_index < len(locations)) else 0
        target_bbox = [locations[idx]]

        encodings = self.face_engine.create_embeddings(pil_img, target_bbox)

        if not encodings:
            return False, "Could not generate face embedding for selected face."
        else:
            encoding = encodings[0]

        # STRICT VALIDATION 3: Person Consistency Check (no different person photos in 1 profile)
        existing_embs = profile.get("embeddings", [])
        if existing_embs and not profile.get("is_group_profile"):
            highest_score = 0.0
            for ref_emb in existing_embs:
                ref_arr = np.asarray(ref_emb, dtype=np.float64)
                score = self.face_engine.calculate_match_score(encoding, ref_arr)
                if score > highest_score:
                    highest_score = score

            if highest_score < 50.0:
                return False, (
                    f"The face in this photo appears to belong to a different person "
                    f"({highest_score:.1f}% match) than the existing reference photos in this profile."
                )

        # Copy reference photo into profile's storage
        ref_id = str(uuid.uuid4())
        ext = image_path.suffix.lower() if image_path.suffix else ".jpg"
        ref_filename = f"ref_{ref_id}{ext}"
        ref_dest_dir = self.profiles_dir / profile_id / "references"
        ref_dest_dir.mkdir(parents=True, exist_ok=True)
        ref_dest_path = ref_dest_dir / ref_filename

        try:
            # Try direct file copy to preserve exact binary quality
            shutil.copy2(image_path, ref_dest_path)
        except Exception:
            # Fallback to PIL save
            save_img = pil_img.convert("RGB") if pil_img.mode != "RGB" else pil_img
            save_img.save(ref_dest_path)

        quality_info = self.assess_reference_quality(pil_img, list(locations[idx]))

        # Record metadata & encoding
        ref_entry = {
            "id": ref_id,
            "filename": ref_filename,
            "bbox": list(locations[idx]),
            "stored_path": str(ref_dest_path),
            "is_fallback": False,
            "quality": quality_info,
        }
        profile.setdefault("references", []).append(ref_entry)
        profile.setdefault("embeddings", []).append(encoding.tolist())

        self._save_profile(profile)
        return True, "Reference photo added successfully"

    def batch_add_reference_photos_from_folder(
        self, profile_id: str, folder_path: Path, recursive: bool = True
    ) -> tuple[int, int, str]:
        """
        Scans all photos in folder_path, extracts face vectors belonging to profile_id,
        and batch imports them into profile.json for continuous learning.
        Returns (added_count, total_scanned_files, message).
        """
        import uuid
        import numpy as np
        from domain.scanner import discover_photos

        profile = self.get_profile(profile_id)
        if not profile:
            return 0, 0, "Profile not found"

        photo_paths = discover_photos([str(folder_path)], recursive=recursive)
        if not photo_paths:
            return 0, 0, "No supported photos found in selected directory"

        added_cnt = 0
        existing_embs = [
            np.asarray(e, dtype=np.float64)
            for e in profile.get("embeddings", [])
            if e is not None and len(e) == 512
        ]

        for p_path in photo_paths:
            try:
                pil_img, err = load_image(p_path)
                if pil_img is None:
                    continue

                locations = self.face_engine.detect_faces(pil_img)
                if not locations:
                    continue

                best_idx = 0
                if len(locations) > 1:
                    if not existing_embs:
                        continue  # Multiple faces and no baseline -> skip to avoid wrong person
                    best_score = -1.0
                    all_embs = self.face_engine.create_embeddings(pil_img, locations)
                    for idx, emb in enumerate(all_embs):
                        for ref_arr in existing_embs:
                            sc = self.face_engine.calculate_match_score(emb, ref_arr)
                            if sc > best_score:
                                best_score = sc
                                best_idx = idx
                    if best_score < 45.0:
                        continue

                target_bbox = locations[best_idx]
                embs = self.face_engine.create_embeddings(pil_img, [target_bbox])
                if not embs:
                    continue

                new_emb = embs[0]

                # Consistency verification if baseline embeddings exist
                if existing_embs:
                    is_consistent = False
                    for ref_arr in existing_embs:
                        sc = self.face_engine.calculate_match_score(new_emb, ref_arr)
                        if sc >= 45.0:
                            is_consistent = True
                            break
                    if not is_consistent:
                        continue

                # Add face crop as reference photo
                crops = self.face_engine.extract_faces(pil_img, [target_bbox])
                face_crop = crops[0] if crops else pil_img

                ref_id = str(uuid.uuid4())
                ref_filename = f"ref_{ref_id}.jpg"
                ref_dest_dir = self.profiles_dir / profile_id / "references"
                ref_dest_dir.mkdir(parents=True, exist_ok=True)
                ref_dest_path = ref_dest_dir / ref_filename

                face_crop.save(ref_dest_path, format="JPEG", quality=92)
                quality_info = self.assess_reference_quality(pil_img, list(target_bbox))

                ref_entry = {
                    "id": ref_id,
                    "filename": ref_filename,
                    "bbox": target_bbox,
                    "stored_path": str(ref_dest_path),
                    "is_fallback": False,
                    "quality": quality_info,
                }

                profile.setdefault("references", []).append(ref_entry)
                profile.setdefault("embeddings", []).append(new_emb.tolist())
                existing_embs.append(new_emb)
                added_cnt += 1

            except Exception as e:
                logger.warning(f"Error processing {p_path} during batch training: {e}")

        if added_cnt > 0:
            self._save_profile(profile)
            msg = f"Successfully added {added_cnt} facial reference vectors from {len(photo_paths)} photos."
        else:
            msg = f"No matching facial vectors found in {len(photo_paths)} photos."

        return added_cnt, len(photo_paths), msg

    @staticmethod
    def assess_reference_quality(pil_img: Image.Image, bbox: list[int]) -> dict[str, Any]:
        """
        Calculates quality rating for a reference face photo crop.
        Returns rating 1 to 5 stars, status description, and star badge string.
        """
        top, right, bottom, left = bbox[0], bbox[1], bbox[2], bbox[3]
        crop_w = max(1, right - left)
        crop_h = max(1, bottom - top)
        face_pixels = crop_w * crop_h

        # Rating evaluation
        if face_pixels >= 15000:
            stars = 5
            label = "🟢 5/5 Stars: Excellent (Sharp & Clear Frontal View)"
        elif face_pixels >= 8000:
            stars = 4
            label = "🟢 4/5 Stars: Good Quality"
        elif face_pixels >= 4000:
            stars = 3
            label = "🟡 3/5 Stars: Moderate (Profile Angle / Slightly Small)"
        elif face_pixels >= 1500:
            stars = 2
            label = "🔴 2/5 Stars: Fair (Low Resolution)"
        else:
            stars = 1
            label = "🔴 1/5 Stars: Low Quality (Tiny Crop)"

        return {
            "stars": stars,
            "badge": "⭐" * stars,
            "quality_label": label,
            "resolution": f"{crop_w}x{crop_h}px",
        }

    def add_reference_photo_direct(
        self,
        profile_id: str,
        image_path: Path,
        embedding: Any,
    ) -> tuple[bool, str]:
        """
        Directly adds a reference photo crop with a pre-computed embedding to a profile.
        Used for unknown face conversion to avoid re-detection failures on tiny crops.
        """
        import numpy as np

        profile = self.get_profile(profile_id)
        if not profile:
            return False, "Profile not found"

        if not image_path.exists():
            return False, f"Image file {image_path} does not exist"

        ref_id = str(uuid.uuid4())
        ext = image_path.suffix.lower() if image_path.suffix else ".jpg"
        ref_filename = f"ref_{ref_id}{ext}"
        ref_dest_dir = self.profiles_dir / profile_id / "references"
        ref_dest_dir.mkdir(parents=True, exist_ok=True)
        ref_dest_path = ref_dest_dir / ref_filename

        shutil.copy2(image_path, ref_dest_path)

        emb_list = embedding.tolist() if isinstance(embedding, np.ndarray) else list(embedding)

        ref_entry = {
            "id": ref_id,
            "filename": ref_filename,
            "bbox": [0, 0, 0, 0],
            "stored_path": str(ref_dest_path),
            "is_fallback": False,
        }

        profile.setdefault("references", []).append(ref_entry)
        profile.setdefault("embeddings", []).append(emb_list)

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
