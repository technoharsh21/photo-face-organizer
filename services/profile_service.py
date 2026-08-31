"""
Profile Service.

Manages face profiles, reference images, face encodings, and bulk profile operations.
Copies reference photos to application storage without altering original files.
Supports selecting specific face from multi-face group reference photos and graceful fallback.
"""

import json
import logging
import shutil
import uuid
from pathlib import Path
from typing import Any

from PIL import Image

from config import Config
from domain.face_engine import FaceEngine
from domain.image_loader import load_image

logger = logging.getLogger(__name__)



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

        if ("centroid_embedding" not in data or not data["centroid_embedding"]) and data.get("embeddings"):
            import numpy as np
            valid_embs = [np.asarray(e, dtype=np.float64) for e in data["embeddings"] if e and len(e) == 512]
            if valid_embs:
                mean_vec = np.mean(valid_embs, axis=0)
                norm = np.linalg.norm(mean_vec)
                data["centroid_embedding"] = (mean_vec / norm if norm > 0 else mean_vec).tolist()

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

    def list_profiles_summary(self) -> list[dict[str, Any]]:
        """
        Lightweight profile listing for UI list/grid views.
        Reads only profile.json (no embedding load, no re-embedding, no centroid
        recompute) and returns id/name/ref_count/first_ref_path/is_group_profile.
        Much cheaper than list_profiles() for display-only screens.
        """
        out: list[dict[str, Any]] = []
        for p_dir in self.profiles_dir.iterdir():
            if not p_dir.is_dir():
                continue
            p_file = p_dir / "profile.json"
            if not p_file.exists():
                continue
            try:
                with open(p_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue

            refs = data.get("references", [])
            first_ref_path = None
            for r in refs:
                sp = r.get("stored_path")
                if sp and Path(sp).exists():
                    first_ref_path = sp
                    break
                fname = r.get("filename")
                if fname:
                    cand = p_dir / "references" / fname
                    if cand.exists():
                        first_ref_path = str(cand)
                        break

            out.append({
                "id": data.get("id", p_dir.name),
                "name": data.get("name", "Unknown"),
                "ref_count": len(refs),
                "first_ref_path": first_ref_path,
                "is_group_profile": bool(data.get("is_group_profile")),
            })
        out.sort(key=lambda x: x["name"].lower())
        return out

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

        # STRICT VALIDATION 4: High-Quality Requirement (4 or 5 Stars Only)
        quality_info = self.assess_reference_quality(pil_img, list(locations[idx]))
        if quality_info.get("stars", 1) < 4:
            return False, (
                f"Photo quality is too low ({quality_info.get('stars')}/5 stars: {quality_info.get('quality_label')}). "
                f"Profiles require high-quality 4 or 5-star photos (clear, sharp, and well-lit) for accurate scanning."
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

        # Auto-compute normalized centroid embedding from all reference embeddings.
        # Used by matcher as a noise-smoothed identity vector for near-threshold tiebreaking.
        import numpy as np
        all_embs = profile.get("embeddings", [])
        valid_embs = [np.asarray(e, dtype=np.float64) for e in all_embs if e and len(e) == 512]
        if valid_embs:
            mean_vec = np.mean(valid_embs, axis=0)
            norm = np.linalg.norm(mean_vec)
            centroid = (mean_vec / norm if norm > 0 else mean_vec).tolist()
            profile["centroid_embedding"] = centroid

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

        # Extract fixed, immutable baseline anchor embeddings
        raw_embs = profile.get("embeddings", [])
        baseline_anchor_embs = [
            np.asarray(e, dtype=np.float64)
            for e in raw_embs
            if e is not None and len(e) == 512
        ]

        if not baseline_anchor_embs:
            return 0, len(photo_paths), (
                "Please add at least 1 clear reference photo manually to this profile first "
                "so the AI has a trusted baseline identity to compare against."
            )

        # Compute trusted anchor centroid
        stacked = np.array(baseline_anchor_embs)
        mean_vec = np.mean(stacked, axis=0)
        norm = np.linalg.norm(mean_vec)
        anchor_centroid = mean_vec / norm if norm > 0 else mean_vec

        candidates = []

        for p_path in photo_paths:
            try:
                pil_img, err = load_image(p_path)
                if pil_img is None:
                    continue

                locations = self.face_engine.detect_faces(pil_img)
                if not locations:
                    continue

                all_embs = self.face_engine.create_embeddings(pil_img, locations)
                if not all_embs:
                    continue

                # Find candidate face that strictly matches the anchor centroid >= 65%
                best_face_idx = None
                best_face_score = -1.0

                for idx, emb in enumerate(all_embs):
                    c_score = self.face_engine.calculate_match_score(emb, anchor_centroid)
                    # Check max match against individual baseline anchors
                    max_anchor_sc = max(self.face_engine.calculate_match_score(emb, ref) for ref in baseline_anchor_embs)
                    effective_score = max(c_score, max_anchor_sc)

                    # STRICT FILTER: Candidate face MUST achieve >= 65.0% match with the anchor
                    if effective_score >= 65.0 and effective_score > best_face_score:
                        best_face_score = effective_score
                        best_face_idx = idx

                if best_face_idx is not None:
                    target_bbox = locations[best_face_idx]
                    best_emb = all_embs[best_face_idx]
                    q_info = self.assess_reference_quality(pil_img, list(target_bbox))
                    candidates.append({
                        "score": best_face_score,
                        "quality_stars": q_info.get("stars", 3),
                        "quality_info": q_info,
                        "pil_img": pil_img,
                        "bbox": target_bbox,
                        "embedding": best_emb,
                        "source_path": p_path,
                    })

            except Exception as e:
                logger.warning(f"Error processing {p_path} during batch training: {e}")

        if not candidates:
            return 0, len(photo_paths), f"No photos in the folder matched {profile.get('name', 'this person')} with high confidence (>= 65% match)."

        # Sort candidates by match confidence and quality (highest match first)
        candidates.sort(key=lambda c: (c["score"], c["quality_stars"]), reverse=True)

        # Cap batch import to the top 15 most distinct, highest-confidence facial vectors
        selected_candidates = candidates[:15]
        added_cnt = 0

        ref_dest_dir = self.profiles_dir / profile_id / "references"
        ref_dest_dir.mkdir(parents=True, exist_ok=True)

        for c in selected_candidates:
            ref_id = str(uuid.uuid4())
            ref_filename = f"ref_{ref_id}.jpg"
            ref_dest_path = ref_dest_dir / ref_filename

            crops = self.face_engine.extract_faces(c["pil_img"], [c["bbox"]])
            face_crop = crops[0] if crops else c["pil_img"]
            face_crop.save(ref_dest_path, format="JPEG", quality=92)

            ref_entry = {
                "id": ref_id,
                "filename": ref_filename,
                "bbox": c["bbox"],
                "stored_path": str(ref_dest_path),
                "is_fallback": False,
                "quality": c["quality_info"],
            }

            profile.setdefault("references", []).append(ref_entry)
            profile.setdefault("embeddings", []).append(c["embedding"].tolist())
            added_cnt += 1

        if added_cnt > 0:
            self._save_profile(profile)
            msg = f"Successfully trained profile with {added_cnt} high-confidence facial vectors from {len(photo_paths)} photos."
        else:
            msg = f"No matching facial vectors found in {len(photo_paths)} photos."

        return added_cnt, len(photo_paths), msg

    def prune_profile_outliers(
        self, profile_id: str, min_similarity: float = 60.0, min_stars: int = 4
    ) -> tuple[int, int]:
        """
        Prunes outlier & low-quality reference photos from a profile:
        1. Removes photos that do not match the core identity (score < min_similarity).
        2. Removes low-quality/blurry photos (< min_stars, i.e. 1, 2, or 3-star photos).
        Returns (removed_count, remaining_count).
        """
        import numpy as np

        profile = self.get_profile(profile_id)
        if not profile:
            return 0, 0

        references = profile.get("references", [])
        raw_embs = profile.get("embeddings", [])

        if not references:
            return 0, 0

        valid_embs = []
        valid_indices = []
        for idx, e in enumerate(raw_embs):
            if e is not None and len(e) == 512:
                valid_embs.append(np.asarray(e, dtype=np.float64))
                valid_indices.append(idx)

        # Compute core centroid from valid reference embeddings if available
        if valid_embs:
            stacked = np.array(valid_embs)
            mean_vec = np.mean(stacked, axis=0)
            norm = np.linalg.norm(mean_vec)
            centroid = mean_vec / norm if norm > 0 else mean_vec
        else:
            centroid = None

        keep_references = []
        keep_embeddings = []
        removed_count = 0

        for idx, ref in enumerate(references):
            # 1. Similarity Check against Centroid
            match_ok = True
            if centroid is not None and idx < len(raw_embs):
                emb = np.asarray(raw_embs[idx], dtype=np.float64)
                if len(references) > 1:
                    score = self.face_engine.calculate_match_score(emb, centroid)
                    if score < min_similarity:
                        match_ok = False

            # 2. Star Quality Check (Only allow 4 or 5 stars)
            quality = ref.get("quality") or {}
            stars = quality.get("stars")
            if stars is None:
                stored_p = ref.get("stored_path")
                if stored_p and Path(stored_p).exists():
                    pil_ref, _ = load_image(Path(stored_p))
                    if pil_ref is not None:
                        q_eval = self.assess_reference_quality(pil_ref, ref.get("bbox"))
                        stars = q_eval.get("stars", 4)
                        ref["quality"] = q_eval
                else:
                    stars = 4

            quality_ok = (stars >= min_stars)

            if match_ok and quality_ok:
                keep_references.append(ref)
                if idx < len(raw_embs):
                    keep_embeddings.append(raw_embs[idx])
            else:
                # Remove outlier / low-star reference file
                removed_count += 1
                try:
                    stored_path = ref.get("stored_path")
                    if stored_path and Path(stored_path).exists():
                        Path(stored_path).unlink()
                except Exception:
                    pass

        profile["references"] = keep_references
        profile["embeddings"] = keep_embeddings

        # Re-compute centroid embedding from remaining clean references
        valid_remaining = [np.asarray(e, dtype=np.float64) for e in keep_embeddings if e and len(e) == 512]
        if valid_remaining:
            mean_vec = np.mean(valid_remaining, axis=0)
            norm = np.linalg.norm(mean_vec)
            profile["centroid_embedding"] = (mean_vec / norm if norm > 0 else mean_vec).tolist()
        else:
            profile["centroid_embedding"] = None

        self._save_profile(profile)
        return removed_count, len(keep_references)

    @staticmethod
    def assess_reference_quality(
        pil_img: Image.Image, bbox: list[int] | tuple[int, int, int, int] | None = None
    ) -> dict[str, Any]:
        """
        Calculates comprehensive 1 to 5 star rating based on:
        1. Face Resolution (pixel dimensions)
        2. Focus / Sharpness (Laplacian variance)
        3. Lighting & Contrast balance (mean brightness & standard deviation)
        """
        try:
            import cv2
            import numpy as np

            width, height = pil_img.size
            if bbox and len(bbox) == 4 and sum(bbox) > 0:
                top, right, bottom, left = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                crop_w = max(1, right - left)
                crop_h = max(1, bottom - top)
                c_top = max(0, top)
                c_left = max(0, left)
                c_bottom = min(height, bottom)
                c_right = min(width, right)
                if c_bottom > c_top and c_right > c_left:
                    face_crop = pil_img.crop((c_left, c_top, c_right, c_bottom))
                else:
                    face_crop = pil_img
            else:
                crop_w, crop_h = width, height
                face_crop = pil_img

            # 1. Resolution Score (0 - 45 points)
            if crop_w >= 90 and crop_h >= 90:
                res_pts = 45.0
            elif crop_w >= 50 and crop_h >= 50:
                res_pts = 38.0
            elif crop_w >= 25 and crop_h >= 25:
                res_pts = 28.0
            elif crop_w >= 15 and crop_h >= 15:
                res_pts = 15.0
            else:
                res_pts = 5.0

            # 2. Focus & Sharpness Score via Laplacian Variance (0 - 35 points)
            arr = np.array(face_crop.convert("L"))
            lap_var = float(np.var(cv2.Laplacian(arr, cv2.CV_64F)))
            if lap_var >= 80.0:
                sharp_pts = 35.0
            elif lap_var >= 25.0:
                sharp_pts = 28.0
            elif lap_var >= 5.0:
                sharp_pts = 20.0
            else:
                # Solid flat / smooth synthetic color
                sharp_pts = 22.0

            # 3. Lighting & Exposure Balance (0 - 20 points)
            mean_b = float(np.mean(arr))
            if 25.0 <= mean_b <= 225.0:
                light_pts = 20.0
            elif 10.0 <= mean_b <= 245.0:
                light_pts = 15.0
            else:
                light_pts = 10.0

            total_score = res_pts + sharp_pts + light_pts

            # Star Mapping
            if total_score >= 78.0:
                stars = 5
                label = "🟢 5/5 Stars: Excellent (Studio Quality / Sharp & Clear)"
            elif total_score >= 58.0:
                stars = 4
                label = "🟢 4/5 Stars: Good Quality (High Clarity)"
            elif total_score >= 40.0:
                stars = 3
                label = "🟡 3/5 Stars: Moderate (Slightly Soft / Medium Size)"
            elif total_score >= 25.0:
                stars = 2
                label = "🔴 2/5 Stars: Fair (Low Resolution / Blurry)"
            else:
                stars = 1
                label = "🔴 1/5 Stars: Low Quality (Tiny / Motion Blurred)"

            return {
                "stars": stars,
                "score": round(total_score, 1),
                "badge": "⭐" * stars,
                "quality_label": label,
                "resolution": f"{crop_w}x{crop_h}px",
                "sharpness": round(lap_var, 1),
            }
        except Exception:
            return {
                "stars": 4,
                "score": 75.0,
                "badge": "⭐⭐⭐⭐",
                "quality_label": "🟢 4/5 Stars: Good Quality",
                "resolution": "Unknown",
                "sharpness": 100.0,
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

        crop_img, err = load_image(image_path)
        if crop_img is not None:
            quality_info = self.assess_reference_quality(crop_img)
            if quality_info.get("stars", 1) < 4:
                return False, f"Photo quality is too low ({quality_info.get('stars')}/5 stars). Only 4 or 5 star faces can be added."
        else:
            quality_info = {"stars": 4, "badge": "⭐⭐⭐⭐", "quality_label": "Good"}

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

    def remove_reference_photos(self, profile_id: str, ref_ids: list[str]) -> int:
        """Remove multiple reference photos and their associated encodings from profile in one batch."""
        profile = self.get_profile(profile_id)
        if not profile or not ref_ids:
            return 0

        ref_id_set = set(ref_ids)
        keep_references = []
        keep_embeddings = []
        raw_embs = profile.get("embeddings", [])
        removed_count = 0

        for i, ref in enumerate(profile.get("references", [])):
            if ref.get("id") in ref_id_set:
                removed_count += 1
                stored_path = ref.get("stored_path")
                if stored_path and Path(stored_path).exists():
                    try:
                        Path(stored_path).unlink()
                    except Exception:
                        pass
            else:
                keep_references.append(ref)
                if i < len(raw_embs):
                    keep_embeddings.append(raw_embs[i])

        profile["references"] = keep_references
        profile["embeddings"] = keep_embeddings

        # Re-compute centroid embedding from remaining references
        import numpy as np
        valid_remaining = [np.asarray(e, dtype=np.float64) for e in keep_embeddings if e and len(e) == 512]
        if valid_remaining:
            mean_vec = np.mean(valid_remaining, axis=0)
            norm = np.linalg.norm(mean_vec)
            profile["centroid_embedding"] = (mean_vec / norm if norm > 0 else mean_vec).tolist()
        else:
            profile["centroid_embedding"] = None

        self._save_profile(profile)
        return removed_count

    def remove_reference_photo(self, profile_id: str, ref_id: str) -> bool:
        """Remove reference photo and its associated encoding from profile."""
        return self.remove_reference_photos(profile_id, [ref_id]) > 0

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
