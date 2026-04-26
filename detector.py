import cv2
import numpy as np
import mediapipe as mp
from config import (
    MP_MODEL_COMPLEXITY,
    MP_DETECTION_CONFIDENCE,
    MP_TRACKING_CONFIDENCE,
)

_mp_hands = mp.solutions.hands
hands = _mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    model_complexity=MP_MODEL_COMPLEXITY,
    min_detection_confidence=MP_DETECTION_CONFIDENCE,
    min_tracking_confidence=MP_TRACKING_CONFIDENCE,
)

def detect_hand_landmarks(frame):
    # [XỬ LÝ ẢNH] Chuyển BGR (OpenCV) → RGB (MediaPipe). Thiếu: model nhận sai kênh màu → landmarks trả về rác hoặc None.
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    # [TỐI ƯU BỘ NHỚ] Ngăn numpy sao chép mảng. Thiếu: cấp phát RAM gấp đôi mỗi frame → FPS tụt, độ trễ tăng mạnh.
    rgb.flags.writeable = False
    results = hands.process(rgb)

    if not results.multi_hand_landmarks:
        return None

    h, w = frame.shape[:2]
    lms = results.multi_hand_landmarks[0].landmark
    return [(int(lm.x * w), int(lm.y * h)) for lm in lms]

def _dist(p1, p2):
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    return (dx * dx + dy * dy) ** 0.5

def get_pinch_data(landmarks):
    if not landmarks or len(landmarks) < 21:
        return None
    thumb_tip  = landmarks[4]
    index_tip  = landmarks[8]
    wrist      = landmarks[0]
    middle_mcp = landmarks[9]

    pinch_dist = _dist(thumb_tip, index_tip)
    palm_width = _dist(wrist, middle_mcp)

    # [CHUẨN HÓA HÌNH HỌC] Tỷ lệ hóa theo kích thước tay (scale-invariant). Thiếu: pinch nhạy với khoảng cách camera → tay tiến/lùi nhận sai lệnh. >10 tránh chia ~0 khi tay xa/mờ.
    norm_dist = pinch_dist / palm_width if palm_width > 10 else 1.0

    return {
        'thumb':      thumb_tip,
        'index':      index_tip,
        'pinch_dist': pinch_dist,
        'palm_width': palm_width,
        'norm_dist':  norm_dist,
    }