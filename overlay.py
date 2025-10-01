# overlay.py
from flask import Flask, Response
import cv2
import mss
import numpy as np

app = Flask(__name__)

model = None         # will be injected from bot.py
monitor_dict = None  # will be injected from bot.py

def set_resources(yolo_model, monitor):
    global model, monitor_dict
    model = yolo_model
    monitor_dict = monitor

def generate_frames():
    with mss.mss() as sct:
        while True:
            sct_img = sct.grab(monitor_dict)
            img = np.array(sct_img)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            results = model.predict(source=img_rgb, conf=0.8, verbose=False)

            if results and len(results[0].boxes) > 0:
                for box in results[0].boxes:
                    x1, y1, x2, y2 = box.xyxy[0]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                    cv2.rectangle(img_rgb, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    x_center = int((x1 + x2) / 2)
                    y_center = int((y1 + y2) / 2)
                    cv2.circle(img_rgb, (x_center, y_center), 5, (0, 0, 255), -1)

            ret, buffer = cv2.imencode('.png', img_rgb)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/png\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def run_overlay():
    print("OBS overlay available at http://localhost:5000/video")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
