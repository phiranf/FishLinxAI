import time
import random
import cv2
import numpy as np
import pyautogui
import pyaudio
import mss
import pyfiglet
import argparse
from ultralytics import YOLO
from colorama import init as initColor, Fore
from humancursor import SystemCursor

from monitor import get_monitor_dict, focus_window

pyautogui.FAILSAFE = False

class WoWFisher:
    GAME_NAME = "World of Warcraft"
    CAST_DURATION_SEC = 30
    DECIBEL_THRESHOLD = -45
    AUDIO_RATE = 44100
    AUDIO_CHUNK = 2048

    # def __init__(self, model_path="best.pt", debug=False):
    def __init__(self, model_path="../runs/detect/train3/weights/best.pt", debug=False, live_view=False):
        initColor()
        self.cursor = SystemCursor()
        self.model = YOLO(model_path).to("cpu")
        self.debug = debug
        self.live_view = live_view

        self.fishing_key = None
        self.lure_key = None
        self.lure_duration = 0
        self.last_lure = None
        self.is_fishing = False
        self.total_caught = 0
        self.had_focus = False

        self.monitor_dict = get_monitor_dict(self.GAME_NAME)

        if self.live_view:
            cv2.namedWindow("WoW Fisher - Live View", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("WoW Fisher - Live View", 800, 600)

    def show_start_text(self):
        ascii_text = pyfiglet.figlet_format("WoW_Fish_YOLO")
        print(Fore.CYAN + ascii_text + Fore.RESET)
        print(Fore.RED + "Do not move your window. Enable auto-loot." + Fore.RESET)
        print(Fore.RED + "First person view + hide UI recommended." + Fore.RESET)
        print("Stop bot with CTRL+C.")

    def configure(self):
        self.fishing_key = input("Provide the key for the fishing spell: ").lower()
        use_lure = input("Do you want to use lure ? (y/n) ").lower()

        if use_lure == "y":
            self.lure_key = input("Provide the key to use lure: ").lower()
            minutes = int(input("Provide the lure duration (in minutes): "))
            self.lure_duration = 60 * minutes

    def get_prediction(self):
        """Grab a single frame and detect bobber; non-blocking"""
        with mss.mss() as sct:
            sct_img = sct.grab(self.monitor_dict)
            img = np.array(sct_img)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            results = self.model.predict(source=img_rgb, conf=0.5, verbose=False)
            x_center_screen, y_center_screen = None, None

            if results and len(results[0].boxes) > 0:
                boxes = results[0].boxes.xyxy.cpu().numpy()
                confidences = results[0].boxes.conf.cpu().numpy()
                idx = int(np.argmax(confidences))
                x1, y1, x2, y2 = boxes[idx]
                x_center = int((x1 + x2) / 2)
                y_center = int((y1 + y2) / 2)
                x_center_screen = self.monitor_dict["left"] + x_center
                y_center_screen = self.monitor_dict["top"] + y_center

                if self.debug or self.live_view:
                    cv2.rectangle(img_rgb, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    cv2.circle(img_rgb, (x_center, y_center), 5, (0, 0, 255), -1)

                    # Add confidence text
                    conf_text = f"Conf: {confidences[idx]:.2f}"
                    cv2.putText(img_rgb, conf_text, (int(x1), int(y1) - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            if self.debug or self.live_view:
                # Add status text
                status_text = "FISHING" if self.is_fishing else "IDLE"
                cv2.putText(img_rgb, status_text, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                cv2.putText(img_rgb, f"Fish caught: {self.total_caught}", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                window_name = "Live Debug" if self.debug else "WoW Fisher - Live View"
                cv2.imshow(window_name, img_rgb)
                cv2.waitKey(1)

            return x_center_screen, y_center_screen

    def catch_fish_with_audio(self, x_center, y_center, max_duration=CAST_DURATION_SEC):
        if not self.is_fishing:
            return False

        mic = pyaudio.PyAudio()
        try:
            stream = mic.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.AUDIO_RATE,
                input=True,
                frames_per_buffer=self.AUDIO_CHUNK,
            )
        except Exception as e:
            print(Fore.RED + f"Audio init error: {e}" + Fore.RESET)
            mic.terminate()
            return False

        start_time = time.time()
        caught = False
        time.sleep(2)  # Prevent immediate recast

        try:
            while time.time() - start_time < max_duration and self.is_fishing:
                try:
                    data = stream.read(self.AUDIO_CHUNK, exception_on_overflow=False)
                except Exception as e:
                    print("Audio stream error:", e)
                    break

                samples = np.frombuffer(data, dtype=np.int16) / 32768.0
                if samples.size == 0:
                    continue

                rms = np.sqrt(np.mean(samples ** 2))
                db = np.round(20 * np.log10(rms + 1e-6))

                if db > self.DECIBEL_THRESHOLD:
                    print(Fore.GREEN + f"Splash detected ({db} dB)! Catching fish..." + Fore.RESET)
                    self.cursor.move_to([x_center, y_center])
                    pyautogui.click(button="right")
                    self.total_caught += 1
                    caught = True
                    break
        finally:
            stream.stop_stream()
            stream.close()
            mic.terminate()

        return caught

    def cast(self):
        print(Fore.CYAN + "\nStart fishing." + Fore.RESET)
        pyautogui.press(self.fishing_key)
        print(Fore.CYAN + "Waiting for a fish..." + Fore.RESET)

        start_time = time.time()
        caught = False

        time.sleep(4)  # Prevent immediate recast

        while (time.time() - start_time < self.CAST_DURATION_SEC) and self.is_fishing:
            x_center, y_center = self.get_prediction()
            if x_center and y_center:
                caught = self.catch_fish_with_audio(
                    x_center,
                    y_center,
                    max_duration=self.CAST_DURATION_SEC - (time.time() - start_time),
                )
                if caught:
                    self.stop()
                    break
            time.sleep(2)

        if not caught:
            print(Fore.MAGENTA + "No fish caught this cast." + Fore.RESET)

        self.restart()

    def focus_or_throw(self):
        try:
            focus_window(self.GAME_NAME)
        except Exception:
            print(Fore.RED + f"No window with {self.GAME_NAME} found. Did you launch the game?" + Fore.RESET)
            exit(1)

    def start(self):
        if not self.had_focus:
            self.focus_or_throw()
            time.sleep(0.5)

        if self.lure_key and (not self.last_lure or time.time() - self.last_lure > self.lure_duration):
            print(f"Attach new lure ({self.lure_key}) for {self.lure_duration / 60} minutes.")
            self.last_lure = time.time()
            pyautogui.press(self.lure_key)
            time.sleep(5)

        self.is_fishing = True
        self.cast()

    def stop(self):
        self.is_fishing = False
        print(f"You caught {self.total_caught} fish this session.")
        if self.debug or self.live_view:
            cv2.destroyAllWindows()

    def restart(self):
        time.sleep(random.uniform(0, 3))
        self.start()

    def run(self):
        self.show_start_text()
        try:
            self.configure()
            self.start()
        except KeyboardInterrupt:
            print(Fore.RED + "Keyboard interrupt received. Exiting..." + Fore.RESET)
            self.stop()
        finally:
            print(Fore.RED + "Clean up and exit." + Fore.RESET)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WoW Fishing Bot with YOLO detection")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--live-view", action="store_true", help="Enable live visualization window")
    parser.add_argument("--model", type=str, default="../runs/detect/train3/weights/best.pt",
                       help="Path to YOLO model weights")
    args = parser.parse_args()

    bot = WoWFisher(model_path=args.model, debug=args.debug, live_view=args.live_view)
    bot.run()
