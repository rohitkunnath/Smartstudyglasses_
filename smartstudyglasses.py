import time
import cv2
import requests
from ultralytics import YOLO
import numpy as np

MODEL_PATH = "dtect.pt"
ESP32_CAM_URL = "http://192.168.1.50:81/stream"
VIBRATOR_ESP32_BASE = "http://192.168.1.60"
VIBRATE_ON_ENDPOINT = "/vibrate/on"
VIBRATE_OFF_ENDPOINT = "/vibrate/off"

TARGET_LABEL = "book"
CONF_THRESHOLD = 0.35
DETECTION_FRAMES_REQUIRED = 3
ABSENCE_FRAMES_REQUIRED = 8
SHOW_WINDOW = True
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
REQUEST_TIMEOUT = 1.5

def send_vibrator_command(on: bool):
    endpoint = VIBRATE_ON_ENDPOINT if on else VIBRATE_OFF_ENDPOINT
    url = VIBRATOR_ESP32_BASE.rstrip("/") + endpoint
    try:
        requests.get(url, timeout=REQUEST_TIMEOUT)
    except:
        pass

def open_stream(url):
    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video stream at {url}.")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    return cap

def draw_boxes(frame, result, names):
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        return frame
    for b in boxes:
        xyxy = b.xyxy[0].cpu().numpy()
        conf = float(b.conf[0].cpu().numpy())
        cls_id = int(b.cls[0].cpu().numpy())
        label = names.get(cls_id, str(cls_id))
        x1, y1, x2, y2 = map(int, xyxy)
        cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,0), 2)
        cv2.putText(frame, f"{label} {conf:.2f}", (x1, y1-6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)
    return frame

def main():
    model = YOLO(MODEL_PATH)
    try:
        cap = open_stream(ESP32_CAM_URL)
    except:
        return

    try:
        if hasattr(model, "model") and hasattr(model.model, "names"):
            names_map = model.model.names
        elif hasattr(model, "names"):
            names_map = model.names
        else:
            names_map = {}
    except:
        names_map = {}

    if isinstance(names_map, (list, tuple)):
        names = {i: n for i, n in enumerate(names_map)}
    else:
        names = dict(names_map)

    present_count = 0
    absent_count = 0
    last_state = None

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(1.0)
                cap.release()
                cap = open_stream(ESP32_CAM_URL)
                continue

            frame_small = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
            results = model.predict(source=frame_small, conf=CONF_THRESHOLD, verbose=False, max_det=50)
            result = results[0]

            detected = False
            boxes = getattr(result, "boxes", None)
            if boxes is not None:
                for b in boxes:
                    conf = float(b.conf[0].cpu().numpy())
                    cls_id = int(b.cls[0].cpu().numpy())
                    label = names.get(cls_id, str(cls_id))
                    if conf >= CONF_THRESHOLD and label.lower() == TARGET_LABEL.lower():
                        detected = True
                        break

            if detected:
                present_count += 1
                absent_count = 0
            else:
                absent_count += 1
                present_count = 0

            new_state = last_state
            if present_count >= DETECTION_FRAMES_REQUIRED:
                new_state = True
            elif absent_count >= ABSENCE_FRAMES_REQUIRED:
                new_state = False

            if new_state != last_state:
                if new_state is True:
                    send_vibrator_command(on=False)
                elif new_state is False:
                    send_vibrator_command(on=True)
                last_state = new_state

            if SHOW_WINDOW:
                vis = frame_small.copy()
                vis = draw_boxes(vis, result, names)
                state_text = "Book: DETECTED" if detected else "Book: NOT DETECTED"
                cv2.putText(vis, state_text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                            (0,0,255) if not detected else (0,255,0), 2)
                cv2.imshow("ESP32-CAM YOLOv8", vis)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
