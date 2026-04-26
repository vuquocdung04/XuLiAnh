import cv2
import socket
import time
import threading
import numpy as np
from config import *
from detector import detect_hand_landmarks, get_pinch_data
from gesture import GestureRecognizer
from one_euro_filter import OneEuroFilter

class CameraThread:
    def __init__(self, src, width, height, fps):
        self.cap = cv2.VideoCapture(src, cv2.CAP_DSHOW if hasattr(cv2, 'CAP_DSHOW') else 0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS,          fps)
        # [GIẢM LATENCY] Chỉ giữ frame mới nhất, xóa hàng đợi I/O
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)
        self.frame   = None
        self.lock    = threading.Lock()
        self.running = False
        self.thread  = None

    def start(self):
        if not self.cap.isOpened(): return False
        self.running = True
        self.thread  = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()
        return True

    def _reader(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = frame
            else:
                time.sleep(0.001)

    def read(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def stop(self):
        self.running = False
        if self.thread: self.thread.join(timeout=1.0)
        self.cap.release()

# [CHỈ GIỮ LẠI TRẠNG THÁI CẦN THIẾT]
app_state = {
    "running":    True,
    "show_debug": SHOW_DEBUG_WINDOW,
}

def on_mouse_click(event, x, y, flags, param):
    if event != cv2.EVENT_LBUTTONDOWN: return
    if 20 <= x <= 280:
        if 20 <= y <= 80:
            app_state["show_debug"] = not app_state["show_debug"]
            if not app_state["show_debug"]:
                try: cv2.destroyWindow("Debug Camera")
                except: pass
        elif 100 <= y <= 140:
            app_state["running"] = False

def draw_control_panel():
    # Giảm chiều cao panel vì chỉ còn 2 nút
    panel = np.ones((160, 300, 3), dtype=np.uint8) * 40
    
    # Nút Debug
    c_debug = (0, 200, 0) if app_state["show_debug"] else (100, 100, 100)
    cv2.rectangle(panel, (20, 20), (280, 80), c_debug, -1)
    cv2.putText(panel, "Camera Debug", (60, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
    
    # Nút Thoát
    cv2.rectangle(panel, (20, 100), (280, 140), (0, 0, 200), -1)
    cv2.putText(panel, "THOAT (Q)", (100, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
    
    return panel

def main():
    cam = CameraThread(CAMERA_ID, CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS)
    if not cam.start():
        print("❌ Không mở được camera.")
        return
    time.sleep(0.4)

    gesture_rec = GestureRecognizer()
    udp_sock    = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setblocking(False)

    filter_x = OneEuroFilter(min_cutoff=OE_MIN_CUTOFF, beta=OE_BETA, d_cutoff=OE_D_CUTOFF)
    filter_y = OneEuroFilter(min_cutoff=OE_MIN_CUTOFF, beta=OE_BETA, d_cutoff=OE_D_CUTOFF)

    last_x, last_y     = 0.5, 0.5
    vx, vy             = 0.0, 0.0          # Vận tốc dự đoán (đơn vị: chuẩn hóa/giây)
    last_frame_time    = 0.0               # Timestamp frame cuối cùng có điểm chạm
    last_send_time     = 0.0
    send_interval      = 1.0 / UDP_SEND_RATE
    frame_count, fps_start = 0, time.time()
    actual_fps             = 0.0

    cv2.namedWindow("Control Panel")
    cv2.setMouseCallback("Control Panel", on_mouse_click)

    print(f"✓ Camera {CAMERA_WIDTH}x{CAMERA_HEIGHT} | UDP {UDP_SEND_RATE} Hz | MP complexity={MP_MODEL_COMPLEXITY}")

    try:
        while app_state["running"]:
            frame = cam.read()
            if frame is None:
                time.sleep(0.001)
                continue

            now = time.time()
            frame_count += 1
            cv2.imshow("Control Panel", draw_control_panel())

            landmarks  = detect_hand_landmarks(frame)
            pinch_data = get_pinch_data(landmarks) if landmarks else None

            # --- XỬ LÝ PINCH ---
            # Luôn bật Hysteresis để chống flicker
            if pinch_data:
                is_pinching = gesture_rec.update(pinch_data['norm_dist'])
            else:
                is_pinching = gesture_rec.update(999.0)

            # --- XỬ LÝ TỌA ĐỘ ---
            if landmarks and pinch_data:
                raw_x = 1.0 - (pinch_data['index'][0] / frame.shape[1])
                raw_y = pinch_data['index'][1] / frame.shape[0]
                
                # Luôn bật 1-Euro Filter để khử jitter & giữ độ trễ thấp
                target_x = filter_x(raw_x, now)
                target_y = filter_y(raw_y, now)
                
                # [TÍNH VẬN TỐC] Cập nhật vx, vy để dùng khi mất landmark
                dt_frame = now - last_frame_time if last_frame_time > 0 else 1.0/30.0
                if dt_frame > 1e-6:
                    vx = (target_x - last_x) / dt_frame
                    vy = (target_y - last_y) / dt_frame
                    
                last_x, last_y = target_x, target_y
                last_frame_time = now
            else:
                # [DỰ ĐOÁN CHUYỂN ĐỘNG] Linear Extrapolation khi tay di chuyển nhanh bị mất điểm chạm
                dt_pred = now - last_frame_time
                target_x = last_x + vx * dt_pred
                target_y = last_y + vy * dt_pred
                last_x, last_y = target_x, target_y

            # Giới hạn tọa độ trong [0, 1]
            target_x = max(0.0, min(1.0, target_x))
            target_y = max(0.0, min(1.0, target_y))

            # Gửi UDP @120Hz cố định
            if now - last_send_time >= send_interval:
                msg = f"{target_x:.4f},{target_y:.4f},{1 if is_pinching else 0}"
                try:
                    udp_sock.sendto(msg.encode('ascii'), (UDP_IP, UDP_PORT))
                except (BlockingIOError, OSError):
                    pass
                last_send_time = now

            if now - fps_start >= 1.0:
                actual_fps = frame_count / (now - fps_start)
                print(f"\r📊 FPS: {actual_fps:5.1f} | Pinch: {'ON' if is_pinching else 'OFF'} ", end="  ")
                frame_count, fps_start = 0, now

            if app_state["show_debug"]:
                debug = frame.copy()
                if landmarks:
                    for i, (x, y) in enumerate(landmarks):
                        color = (0, 255, 0) if i in (4, 8) else (255, 255, 255)
                        cv2.circle(debug, (x, y), 4, color, -1)
                    if pinch_data:
                        line_color = (0, 255, 0) if is_pinching else (0, 0, 255)
                        cv2.line(debug, pinch_data['thumb'], pinch_data['index'], line_color, 2)
                        cv2.putText(debug, f"norm: {pinch_data['norm_dist']:.2f}", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                cv2.putText(debug, f"FPS: {actual_fps:.0f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(debug, f"Pinch: {'ON' if is_pinching else 'OFF'}", (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if is_pinching else (0, 0, 255), 2)
                cv2.imshow("Debug Camera", debug)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'): app_state["running"] = False
            elif key == ord('w'):
                app_state["show_debug"] = not app_state["show_debug"]
                if not app_state["show_debug"]:
                    try: cv2.destroyWindow("Debug Camera")
                    except: pass

    finally:
        cam.stop()
        udp_sock.close()
        cv2.destroyAllWindows()
        print("\n✓ Đã đóng chương trình an toàn")

if __name__ == "__main__":
    main()