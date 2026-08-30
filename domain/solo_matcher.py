"""
Solo Face Matcher Module.

Evaluates detected faces in a photo strictly for single-person (solo) matching.
Rejects photos containing 2 or more faces (group photos) to ensure person folders
contain ONLY solo photos.
"""

import itertools
from typing import Any
import numpy as np

from domain.face_engine import FaceEngine
from domain.matcher import ProfileMatchResult
from services.classifier_service import ProfileClassifierService


class SoloFaceMatcher:
    """
    Face matcher dedicated to solo photo organization.
    Only matches photos where len(face_locations) == 1 (or exact N for exclusive group profiles).
    Uses precision threshold (default 70.0%) to prevent false-positive person matches.
    """

    def __init__(self, face_engine: FaceEngine, threshold: float = 70.0):
        self.face_engine = face_engine
        self.threshold = threshold
        self.classifier_service = ProfileClassifierService()
        self._last_profile_count = -1

    def match_face(
        self,
        face_encoding: np.ndarray,
        profiles: list[dict[str, Any]],
        bounding_box: tuple[int, int, int, int] | None = None,
        face_index: int = 0,
    ) -> ProfileMatchResult:
        """
        Evaluate a single face encoding against individual profiles.
        Ignores group profiles and enforces precision threshold.
        """
        best_match_id = None
        best_match_name = None
        highest_score = 0.0
        profile_best_scores: dict[str, float] = {}

        # Auto-train fast discriminative classifier on-device when profile set changes
        if len(profiles) != self._last_profile_count:
            self.classifier_service.train_classifier(profiles)
            self._last_profile_count = len(profiles)

        for profile in profiles:
            p_id = profile["id"]
            p_name = profile["name"]
            if profile.get("is_group_profile"):
                continue

            embeddings = profile.get("embeddings", [])
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
            best_raw = sorted_scores[0]

            # Consensus boost: small confidence boost when 2+ references agree the face matches.
            if len(sorted_scores) >= 2 and sorted_scores[1] >= 45.0:
                consensus_boost = min(5.0, (sorted_scores[1] / 100.0) * 8.0)
                p_best_score = min(100.0, best_raw + consensus_boost)
            else:
                p_best_score = best_raw

            # Centroid tiebreaker: for near-threshold scores, compare against profile's mean centroid
            centroid = profile.get("centroid_embedding")
            if centroid is not None and len(centroid) == 512:
                centroid_arr = np.asarray(centroid, dtype=np.float64)
                centroid_score = self.face_engine.calculate_match_score(face_encoding, centroid_arr)
                if centroid_score > p_best_score:
                    p_best_score = centroid_score

            # Apply discriminative SVM classifier margin adjustment
            final_p_score = self.classifier_service.evaluate_discriminative_margin(
                face_encoding, p_id, p_best_score
            )

            profile_best_scores[p_id] = final_p_score

            if final_p_score >= self.threshold and final_p_score > highest_score:
                highest_score = final_p_score
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
        all_system_profiles: list[dict[str, Any]] | None = None,
    ) -> tuple[set[str], list[ProfileMatchResult]]:
        """
        Evaluates detected faces in a photo for solo and exclusive group matching.

        RULES:
        1. Individual Solo Profile:
           - Matches ONLY when len(face_locations) == 1.
           - Single face must match individual profile with score >= threshold.
        2. Group Solo Profile (e.g. Couple / Family Group):
           - Matches ONLY when len(face_locations) == N (exact member count).
           - Every compulsory member of the Group Profile must match a distinct face with score >= threshold.
           - Guarantees 0% strangers/outsiders in the photo.

        :return: (set_of_matched_profile_names, list_of_face_results)
        """
        face_results: list[ProfileMatchResult] = []
        matched_profile_names: set[str] = set()

        # Separate selected profiles into individual and group profiles
        individual_profiles = [p for p in profiles if not p.get("is_group_profile")]
        group_profiles = [p for p in profiles if p.get("is_group_profile")]

        # 1. Individual Solo Matching (Requires EXACTLY 1 face)
        if len(face_locations) == 1:
            res = self.match_face(face_encodings[0], individual_profiles, bounding_box=face_locations[0], face_index=0)
            face_results.append(res)
            if res.is_match and res.matched_profile_name:
                matched_profile_names.add(res.matched_profile_name)
        else:
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

        # 2. Exclusive Group Solo Matching
        num_faces = len(face_locations)
        system_profiles_map = {
            p["id"]: p for p in (all_system_profiles or profiles)
        }

        for g_profile in group_profiles:
            comp_ids = g_profile.get("compulsory_profile_ids", [])
            required_count = len(comp_ids)

            # Rule 1: Exact face count match (photo face count MUST equal group member count)
            if required_count > 1 and num_faces == required_count:
                member_profiles = [system_profiles_map[cid] for cid in comp_ids if cid in system_profiles_map]
                if len(member_profiles) == required_count:
                    # Rule 2: Verify every compulsory member is present with score >= threshold
                    all_matched = self._verify_group_member_presence(face_encodings, member_profiles)
                    if all_matched:
                        matched_profile_names.add(g_profile["name"])

        return matched_profile_names, face_results

    def _verify_group_member_presence(
        self,
        face_encodings: list[np.ndarray],
        member_profiles: list[dict[str, Any]],
    ) -> bool:
        """
        Verifies that every compulsory member profile matches a distinct detected face in the photo.
        Uses exact permutation matching (optimal 1-to-1 bijection) to avoid order-dependent false rejections.
        Returns True if 100% of member profiles are present with score >= self.threshold.
        """
        if len(face_encodings) != len(member_profiles):
            return False

        n = len(member_profiles)
        if n == 0:
            return False

        # Build score matrix: scores_matrix[m_idx][f_idx] is best match score between member m and face f
        scores_matrix = []
        for m_prof in member_profiles:
            embeddings = m_prof.get("embeddings", [])
            if not embeddings:
                return False

            centroid = m_prof.get("centroid_embedding")
            centroid_arr = np.asarray(centroid, dtype=np.float64) if (centroid and len(centroid) == 512) else None

            m_row = []
            for face_enc in face_encodings:
                best_sc = 0.0
                for ref_emb in embeddings:
                    ref_arr = np.asarray(ref_emb, dtype=np.float64)
                    if np.all(ref_arr == 0):
                        continue
                    sc = self.face_engine.calculate_match_score(face_enc, ref_arr)
                    if sc > best_sc:
                        best_sc = sc

                if centroid_arr is not None:
                    c_sc = self.face_engine.calculate_match_score(face_enc, centroid_arr)
                    if c_sc > best_sc:
                        best_sc = c_sc

                m_row.append(best_sc)
            scores_matrix.append(m_row)

        # Check if there exists any 1-to-1 assignment where every member matches a distinct face >= threshold
        for perm in itertools.permutations(range(len(face_encodings)), n):
            if all(scores_matrix[i][perm[i]] >= self.threshold for i in range(n)):
                return True

        return False
