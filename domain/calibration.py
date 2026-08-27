"""
Centralized Score Calibration Module.

Converts face_recognition Euclidean distances into a calibrated 0-100 score.
Strictly maps:
  distance = 0.0  -> score = 100.0
  distance = 0.6  -> score = 50.0   (Default threshold boundary)
  distance >= 1.0 -> score = 0.0
"""

def calibrate_match_score(distance: float) -> float:
    """
    Calibrates a face encoding Euclidean distance to a 0-100 match score.
    
    Args:
        distance: float Euclidean distance between two face encodings.
                  Lower values mean higher similarity.
                  
    Returns:
        float score clamped strictly between 0.0 and 100.0.
    """
    if distance is None or distance < 0.0:
        return 0.0
    
    # Distance <= 0.6 maps linearly from 100.0 down to 50.0
    if distance <= 0.6:
        score = 100.0 - (distance / 0.6) * 50.0
    else:
        # Distance between 0.6 and 1.0 maps linearly from 50.0 down to 0.0
        # Distance > 1.0 maps to 0.0
        score = 50.0 * (1.0 - distance) / 0.4
        
    return float(max(0.0, min(100.0, round(score, 2))))
