"""
Face Matcher Module.

Implements profile matching logic for individual faces, group photos, and compulsory multi-person group profiles.
Centralized calibration function enforces threshold (default 50.0).
Rules:
- For a single face: Highest scoring profile wins. Score >= threshold -> Match.
- For a group photo: Photo is copied to every profile that matched a face in the photo.
- For a Group Profile (e.g. "Me & Friend"): Compulsory matching requires ALL specified persons to be present in the photo.
"""

from typing import Any

import numpy as np

from domain.face_engine import FaceEngine


class ProfileMatchResult:
    """Holds match result details for a single detected face."""

    def __init__(
        self,
        face_index: int,
        bounding_box: tuple[int, int, int, int],
        face_encoding: np.ndarray,
        matched_profile_id: str | None,
        matched_profile_name: str | None,
        match_score: float,
        profile_scores: dict[str, float],
    ):
        self.face_index = face_index
        self.bounding_box = bounding_box
        self.face_encoding = face_encoding
        self.matched_profile_id = matched_profile_id
        self.matched_profile_name = matched_profile_name
        self.match_score = match_score
        self.profile_scores = profile_scores

    @property
    def is_match(self) -> bool:
        return self.matched_profile_id is not None


from services.classifier_service import ProfileClassifierService


class FaceMatcher:
    """
    Evaluates detected face encodings against reference profiles.
    """

    def __init__(self, face_engine: FaceEngine, threshold: float = 50.0):
        self.face_engine = face_engine
        self.threshold = threshold
        self.classifier_service = ProfileClassifierService()
        self._last_profile_count = -1

    def match_face(
        self,
        face_encoding: np.ndarray,
        profiles: list[dict[str, Any]],
        bounding_box: tuple[int, int, int, int] = (0, 0, 0, 0),
        face_index: int = 0,
    ) -> ProfileMatchResult:
        """
        Compare a single face encoding against all active profiles.
        """
        profile_best_scores: dict[str, float] = {}
        best_profile_id: str | None = None
        best_profile_name: str | None = None
        highest_score: float = -1.0

        # Auto-train fast discriminative classifier on-device when profile set changes
        if len(profiles) != self._last_profile_count:
            self.classifier_service.train_classifier(profiles)
            self._last_profile_count = len(profiles)

        for profile in profiles:
            # Skip Group Profiles during individual face matching (Group Profiles are evaluated holistically in evaluate_photo_matches)
            if profile.get("is_group_profile"):
                continue

            p_id = profile["id"]
            p_name = profile.get("name", "Unknown")
            embeddings = profile.get("embeddings", [])

            if not embeddings:
                profile_best_scores[p_id] = 0.0
                continue

            scores = []
            for ref_emb in embeddings:
                ref_arr = np.asarray(ref_emb, dtype=np.float64)
                if ref_arr.size > 0:
                    score = self.face_engine.calculate_match_score(face_encoding, ref_arr)
                    scores.append(score)

            if not scores:
                profile_best_scores[p_id] = 0.0
                continue

            sorted_scores = sorted(scores, reverse=True)
            if len(sorted_scores) >= 3:
                # Robust Consensus Scoring: requires support from multiple reference vectors
                best_p_score = 0.60 * sorted_scores[0] + 0.25 * sorted_scores[1] + 0.15 * sorted_scores[2]
            elif len(sorted_scores) == 2:
                best_p_score = 0.70 * sorted_scores[0] + 0.30 * sorted_scores[1]
            else:
                best_p_score = sorted_scores[0]

            # Apply discriminative SVM classifier margin adjustment
            final_p_score = self.classifier_service.evaluate_discriminative_margin(
                face_encoding, p_id, best_p_score
            )

            profile_best_scores[p_id] = final_p_score

            if final_p_score > highest_score:
                highest_score = final_p_score
                best_profile_id = p_id
                best_profile_name = p_name

        if highest_score >= self.threshold and best_profile_id is not None:
            return ProfileMatchResult(
                face_index=face_index,
                bounding_box=bounding_box,
                face_encoding=face_encoding,
                matched_profile_id=best_profile_id,
                matched_profile_name=best_profile_name,
                match_score=highest_score,
                profile_scores=profile_best_scores,
            )
        else:
            return ProfileMatchResult(
                face_index=face_index,
                bounding_box=bounding_box,
                face_encoding=face_encoding,
                matched_profile_id=None,
                matched_profile_name=None,
                match_score=max(0.0, highest_score),
                profile_scores=profile_best_scores,
            )

    def evaluate_photo_matches(
        self,
        face_encodings: list[np.ndarray],
        face_locations: list[tuple[int, int, int, int]],
        profiles: list[dict[str, Any]],
    ) -> tuple[set[str], list[ProfileMatchResult]]:
        """
        Evaluates all detected faces in a photo against profiles.

        Handles:
        1. Individual profile matching for each face.
        2. Compulsory multi-person Group Profiles (if profile has 'compulsory_profile_ids' or 'is_group_profile').
        3. Routing photo to matched individual profile folders AND group profile folder.

        :return: (set_of_matched_profile_names, list_of_individual_face_results)
        """
        face_results: list[ProfileMatchResult] = []
        matched_profile_ids: set[str] = set()
        matched_profile_names: set[str] = set()

        # 1. Match each individual face in the photo
        for idx, (loc, enc) in enumerate(zip(face_locations, face_encodings)):
            res = self.match_face(enc, profiles, bounding_box=loc, face_index=idx)
            face_results.append(res)
            if res.is_match and res.matched_profile_id and res.matched_profile_name:
                matched_profile_ids.add(res.matched_profile_id)
                matched_profile_names.add(res.matched_profile_name)

        existing_ids = {p["id"] for p in profiles}

        # 2. Check Compulsory Group Profiles (e.g. "Me & Friend" or multi-photo Group Profile)
        for profile in profiles:
            if profile.get("is_group_profile"):
                raw_required_ids = set(profile.get("compulsory_profile_ids", []))
                valid_required_ids = {pid for pid in raw_required_ids if pid in existing_ids}

                if len(valid_required_ids) >= 2:
                    # Checked linked individual profiles (must have at least 2 valid profiles)
                    if valid_required_ids.issubset(matched_profile_ids):
                        matched_profile_names.add(profile["name"])
                        matched_profile_ids.add(profile["id"])
                else:
                    # Check reference photos added directly to this Group Profile
                    embeddings = profile.get("embeddings", [])
                    if len(embeddings) >= 2:
                        all_refs_matched = True
                        for ref_emb in embeddings:
                            ref_arr = np.asarray(ref_emb, dtype=np.float64)
                            ref_matched = False
                            for enc in face_encodings:
                                score = self.face_engine.calculate_match_score(enc, ref_arr)
                                if score >= self.threshold:
                                    ref_matched = True
                                    break
                            if not ref_matched:
                                all_refs_matched = False
                                break

                        if all_refs_matched:
                            matched_profile_names.add(profile["name"])
                            matched_profile_ids.add(profile["id"])

        return matched_profile_names, face_results
