from domain.face_engine import FaceEngine


class _StubEngine(FaceEngine):
    def detect_faces(self, image, model="hog", det_thresh=None):
        return [(10, 90, 100, 20)]

    def extract_faces(self, image, face_locations=None):
        return []

    def create_embeddings(self, image, face_locations=None):
        return []

    def compare_embeddings(self, e1, e2):
        return 0.0

    def calculate_match_score(self, e1, e2):
        return 0.0

    def set_device_preference(self, preference):
        return "CPU"

    def get_device_info(self):
        return {}


def test_base_detect_faces_with_kps_fallback():
    eng = _StubEngine()
    result = eng.detect_faces_with_kps(None)
    assert result == [((10, 90, 100, 20), None)]
