"""
Solo Face Matcher Module.

Evaluates detected faces in a photo strictly for single-person (solo) matching.
Rejects photos containing 2 or more faces (group photos) to ensure person folders
contain ONLY solo photos.
"""

from typing import Any
import numpy as np

from domain.face_engine import FaceEngine
from domain.matcher import ProfileMatchResult


class SoloFaceMatcher:
    """
    Face matcher dedicated to solo photo organization.
    Only matches photos where len(face_locations) == 1.
    Uses high-precision threshold (default 70.0%) to prevent false-positive person matches.
    """

    def __init__(self, face_engine: FaceEngine, threshold: float = 70.0):
        self.face_engine = face_engine
        self.threshold = threshold

    def match_face(
        self,
        face_encoding: np.ndarray,
        profiles: list[dict[str, Any]],
        bounding_box: tuple[int, int, int, int] | None = None,
        face_index: int = 0,
    ) -> ProfileMatchResult:
        """
        Evaluate a single face encoding against individual profiles.
        Ignores group profiles and enforces strict 70%+ score threshold.
        """
        best_match_id = None
        best_match_name = None
        highest_score = 0.0
        profile_best_scores: dict[str, float] = {}

        for profile in profiles:
            p_id = profile["id"]
            p_name = profile["name"]
            if profile.get("is_group_profile"):
                continue

            embeddings = profile.get("embeddings", [])
            p_best_score = 0.0

            for ref_emb in embeddings:
                ref_arr = np.asarray(ref_emb, dtype=np.float64)
                # Ignore invalid or all-zero fallback embeddings
                if np.all(ref_arr == 0):
                    continue

                score = self.face_engine.calculate_match_score(face_encoding, ref_arr)
                if score > p_best_score:
                    p_best_score = score

            profile_best_scores[p_id] = p_best_score

            if p_best_score >= self.threshold and p_best_score > highest_score:
                highest_score = p_best_score
                best_match_id = p_id
                best_match_name = p_name

        is_match = best_match_id is not None
        return ProfileMatchResult(
            face_index=face_index,
            bounding_box=bounding_box or (0, 0, 0, 0),
            face_encoding=face_encoding,
            matched_profile_id=best_match_id if is_match else None,
            matched_profile_name=best_match_name if is_match else None,
            match_score=max(0.0, highest_score),
            profile_scores=profile_best_scores,
        )

    def evaluate_solo_photo_matches(
        self,
        face_encodings: list[np.ndarray],
        face_locations: list[tuple[int, int, int, int]],
        profiles: list[dict[str, Any]],
    ) -> tuple[set[str], list[ProfileMatchResult]]:
        """
        Evaluates detected faces in a photo for solo matching.

        RULE:
        - If len(face_locations) == 1: Evaluate single face against individual profiles.
        - If len(face_locations) != 1 (0 faces or 2+ faces): Exclude photo from solo profile folders.

        :return: (set_of_matched_profile_names, list_of_face_results)
        """
        face_results: list[ProfileMatchResult] = []
        matched_profile_names: set[str] = set()

        # STRICT SOLO FILTER: Reject group photos (2+ faces)
        if len(face_locations) != 1:
            # Group photo or no faces -> Do not route to individual solo folders
            for idx, (loc, enc) in enumerate(zip(face_locations, face_encodings)):
                face_results.append(
                    ProfileMatchResult(
                        face_index=idx,
                        bounding_box=loc,
                        face_encoding=enc,
                        matched_profile_id=None,
                        matched_profile_name=None,
                        match_score=0.0,
                        profile_scores={},
                    )
                )
            return set(), face_results

        # Exactly 1 face in photo -> Match against individual profiles
        res = self.match_face(face_encodings[0], profiles, bounding_box=face_locations[0], face_index=0)
        face_results.append(res)
        if res.is_match and res.matched_profile_name:
            matched_profile_names.add(res.matched_profile_name)

        return matched_profile_names, face_results
