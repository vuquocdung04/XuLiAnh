from config import (
    PINCH_ENTER_THRESHOLD,
    PINCH_EXIT_THRESHOLD,
    DEBOUNCE_FRAMES,
)

class GestureRecognizer:
    def __init__(self):
        self.consecutive_pinch   = 0
        self.consecutive_release = 0
        self.current_state       = "RELEASED"

    def update(self, norm_dist):
        if self.current_state == "RELEASED":
            # [CHỐNG FLICKER] Hysteresis: cần norm_dist < ENTER mới chuyển sang PINCHED. Thiếu: dao động sát ngưỡng → Unity bắt/thả liên tục.
            if norm_dist < PINCH_ENTER_THRESHOLD:
                self.consecutive_pinch += 1
                self.consecutive_release = 0
            else:
                self.consecutive_pinch = 0

            # [ỔN ĐỊNH TRẠNG THÁI] Debounce: cần đủ N frame liên tục mới đổi trạng thái. Thiếu: 1 frame nhiễu gây lệnh sai → điều khiển không chính xác.
            if self.consecutive_pinch >= DEBOUNCE_FRAMES:
                self.current_state = "PINCHED"

        else:  # PINCHED
            # [CHỐNG FLICKER] Hysteresis: cần norm_dist > EXIT mới chuyển sang RELEASED. Tạo "dead-zone" giữ trạng thái ổn định.
            if norm_dist > PINCH_EXIT_THRESHOLD:
                self.consecutive_release += 1
                self.consecutive_pinch = 0
            else:
                self.consecutive_release = 0

            if self.consecutive_release >= DEBOUNCE_FRAMES:
                self.current_state = "RELEASED"

        return self.current_state == "PINCHED"

    def reset(self):
        self.consecutive_pinch   = 0
        self.consecutive_release = 0
        self.current_state       = "RELEASED"