"""WoW Fishing Bot with YOLO detection - Refactored version."""

import time
import random
import argparse
import logging
from typing import Optional, Tuple

import cv2
import numpy as np
import pyautogui
import mss
import pyfiglet
from ultralytics import YOLO
from colorama import Fore, Style
from humancursor import SystemCursor

# Local imports
from config import FishingConfig
from logger import setup_logger, get_logger
from audio_detector import AudioDetector
from visualization import VisualizationHandler
from statistics import FishingStatistics
from bot_states import BotState
from monitor import get_monitor_dict, focus_window

pyautogui.FAILSAFE = False


class WoWFisher:
    """
    Automated fishing bot for World of Warcraft using YOLO object detection
    and audio-based fish bite detection.
    """

    def __init__(self, config: FishingConfig):
        """
        Initialize the fishing bot.

        Args:
            config: Configuration object with all bot settings
        """
        self.config = config
        self.logger = setup_logger(
            level=logging.DEBUG if config.debug else logging.INFO
        )

        # Initialize state
        self.state = BotState.IDLE
        self.running = False

        # Initialize statistics
        self.stats = FishingStatistics()

        # Initialize cursor controller
        self.cursor = SystemCursor()

        # Load YOLO model
        self.logger.info(f"Loading YOLO model from {config.model_path}")
        try:
            self.model = YOLO(config.model_path).to("cpu")
            self.logger.info("Model loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            raise

        # Get game window monitor info
        self.logger.info(f"Looking for game window: {config.game_window_name}")
        self.monitor_dict = get_monitor_dict(config.game_window_name)
        if not self.monitor_dict:
            self.logger.error(f"Could not find window: {config.game_window_name}")
            raise RuntimeError(f"Game window '{config.game_window_name}' not found")

        # Initialize screen capture (reusable)
        self.sct = mss.mss()

        # Initialize audio detector
        self.audio = AudioDetector(
            rate=config.audio_rate,
            chunk_size=config.audio_chunk,
            threshold_db=config.decibel_threshold
        )

        # Initialize visualization if enabled
        self.visualizer: Optional[VisualizationHandler] = None
        if config.live_view or config.debug:
            window_name = "Debug View" if config.debug else "WoW Fisher - Live View"
            self.visualizer = VisualizationHandler(
                window_name=window_name,
                enabled=True,
                monitor_id=config.viz_window_monitor,
                width=config.viz_window_width,
                height=config.viz_window_height,
                x_pos=config.viz_window_x,
                y_pos=config.viz_window_y,
                show_fps=config.viz_show_fps,
                show_audio_graph=config.viz_show_audio_graph
            )

        # Lure tracking
        self.last_lure_time: Optional[float] = None

        self.logger.info("Fisher bot initialized successfully")

    def _set_state(self, new_state: BotState) -> None:
        """
        Update bot state and log the change.

        Args:
            new_state: New state to transition to
        """
        if self.state != new_state:
            self.logger.debug(f"State: {self.state} -> {new_state}")
            self.state = new_state

    def show_banner(self) -> None:
        """Display startup banner."""
        ascii_art = pyfiglet.figlet_format("WoW Fish YOLO")
        print(Fore.CYAN + ascii_art + Style.RESET_ALL)
        print(Fore.YELLOW + "Automated Fishing Bot with YOLO Detection" + Style.RESET_ALL)
        print(Fore.RED + "\nIMPORTANT:" + Style.RESET_ALL)
        print("  • Do not move the game window")
        print("  • Enable auto-loot in game")
        print("  • First-person view recommended")
        print("  • Hide UI (ALT+Z) for best results")
        print(Fore.YELLOW + "\nPress CTRL+C to stop\n" + Style.RESET_ALL)

    def focus_game_window(self) -> bool:
        """
        Focus the game window.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.debug("Focusing game window")
            focus_window(self.config.game_window_name)
            time.sleep(self.config.window_focus_wait_sec)
            return True
        except Exception as e:
            self.logger.error(f"Failed to focus game window: {e}")
            return False

    def should_apply_lure(self) -> bool:
        """
        Check if lure should be applied.

        Returns:
            True if lure needs to be applied
        """
        if not self.config.lure_key:
            return False

        lure_duration_sec = self.config.lure_duration_minutes * 60

        if self.last_lure_time is None:
            return True

        return (time.time() - self.last_lure_time) > lure_duration_sec

    def apply_lure(self) -> None:
        """Apply fishing lure with visualization updates."""
        self._set_state(BotState.APPLYING_LURE)
        self.logger.info(
            f"Applying lure (key: {self.config.lure_key}, "
            f"duration: {self.config.lure_duration_minutes}m)"
        )

        pyautogui.press(self.config.lure_key)
        self.last_lure_time = time.time()

        # Wait with visualization updates
        lure_start = time.time()
        while time.time() - lure_start < self.config.lure_apply_wait_sec:
            if self.visualizer:
                sct_img = self.sct.grab(self.monitor_dict)
                img = np.array(sct_img)
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

                extra_info = [
                    f"Applying lure...",
                    f"Wait: {int(self.config.lure_apply_wait_sec - (time.time() - lure_start))}s"
                ]

                img_rgb = self.visualizer.draw_status(
                    img_rgb,
                    status=str(self.state),
                    fish_count=self.stats.successful_catches,
                    audio_level=self.audio.get_current_level(),
                    extra_info=extra_info,
                    threshold=self.config.decibel_threshold
                )
                self.visualizer.show(img_rgb)

            time.sleep(0.1)

    def capture_and_detect(self) -> Tuple[Optional[np.ndarray], Optional[Tuple[int, int]], Optional[float]]:
        """
        Capture screen and detect bobber.

        Returns:
            Tuple of (image, bobber_center_screen_coords, confidence)
        """
        # Capture screen
        sct_img = self.sct.grab(self.monitor_dict)
        img = np.array(sct_img)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        # Run YOLO detection
        results = self.model.predict(
            source=img_rgb,
            conf=self.config.confidence_threshold,
            verbose=False
        )

        # Process results
        if not results or len(results[0].boxes) == 0:
            self.stats.record_detection(success=False)
            return img_rgb, None, None

        # Get best detection
        boxes = results[0].boxes.xyxy.cpu().numpy()
        confidences = results[0].boxes.conf.cpu().numpy()
        best_idx = int(np.argmax(confidences))

        x1, y1, x2, y2 = boxes[best_idx]
        confidence = float(confidences[best_idx])

        # Calculate center in screen coordinates
        x_center = int((x1 + x2) / 2)
        y_center = int((y1 + y2) / 2)
        x_screen = self.monitor_dict["left"] + x_center
        y_screen = self.monitor_dict["top"] + y_center

        self.stats.record_detection(success=True)

        # Visualize if enabled
        if self.visualizer:
            img_rgb = self.visualizer.draw_detection(
                img_rgb,
                bbox=(int(x1), int(y1), int(x2), int(y2)),
                confidence=confidence,
                center=(x_center, y_center)
            )

        return img_rgb, (x_screen, y_screen), confidence

    def wait_for_bite(self, bobber_position: Tuple[int, int], max_duration: float, cast_start: float) -> bool:
        """
        Wait for fish to bite using audio detection with continuous visualization updates.

        Args:
            bobber_position: Screen coordinates of bobber (x, y)
            max_duration: Maximum time to wait in seconds
            cast_start: Timestamp when cast started (for display)

        Returns:
            True if fish caught, False otherwise
        """
        self._set_state(BotState.WAITING_FOR_BITE)
        self.logger.info("Waiting for fish to bite...")

        start_time = time.time()
        time.sleep(self.config.audio_wait_sec)  # Initial delay

        # Continuously check audio and update visualization
        while time.time() - start_time < max_duration:
            # Check audio level
            current_level = self.audio.get_current_level()

            if current_level is not None and current_level > self.config.decibel_threshold:
                self._set_state(BotState.CATCHING)
                self.logger.info(f"Splash detected! ({current_level:.1f} dB) Clicking at {bobber_position}")

                # Move cursor and click
                self.cursor.move_to(list(bobber_position))
                pyautogui.click(button="right")

                self._set_state(BotState.LOOTING)
                time.sleep(1.5)  # Wait for loot

                return True

            # Update visualization with continuous feed
            if self.visualizer:
                # Capture current frame
                sct_img = self.sct.grab(self.monitor_dict)
                img = np.array(sct_img)
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

                # Draw bobber position marker (where we're watching)
                if bobber_position:
                    # Convert screen coords to image coords
                    x_img = bobber_position[0] - self.monitor_dict["left"]
                    y_img = bobber_position[1] - self.monitor_dict["top"]

                    # Draw a persistent indicator showing bobber location
                    cv2.circle(img_rgb, (x_img, y_img), 8, (0, 255, 255), 2)
                    cv2.circle(img_rgb, (x_img, y_img), 3, (0, 255, 255), -1)
                    cv2.putText(img_rgb, "WATCHING", (x_img - 40, y_img - 15),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

                extra_info = [
                    f"Cast: {self.stats.total_casts}",
                    f"Time: {int(time.time() - cast_start)}s",
                    f"Waiting: {int(time.time() - start_time)}s"
                ]

                img_rgb = self.visualizer.draw_status(
                    img_rgb,
                    status=str(self.state),
                    fish_count=self.stats.successful_catches,
                    audio_level=current_level,
                    extra_info=extra_info,
                    threshold=self.config.decibel_threshold
                )
                self.visualizer.show(img_rgb)

            # Small delay to avoid excessive CPU usage
            time.sleep(0.1)

        return False

    def perform_cast(self) -> bool:
        """
        Perform a complete fishing cast cycle.

        Returns:
            True if fish was caught, False otherwise
        """
        self.stats.record_cast()
        cast_start = time.time()

        # Cast fishing line
        self._set_state(BotState.CASTING)
        self.logger.info(f"Casting fishing line (key: {self.config.fishing_key})")
        pyautogui.press(self.config.fishing_key)

        # Wait for cast animation with visualization updates
        cast_wait_start = time.time()
        while time.time() - cast_wait_start < self.config.initial_wait_sec:
            if self.visualizer:
                # Capture and show frame during cast animation
                sct_img = self.sct.grab(self.monitor_dict)
                img = np.array(sct_img)
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

                extra_info = [
                    f"Cast: {self.stats.total_casts}",
                    f"Time: {int(time.time() - cast_start)}s",
                    "Casting animation..."
                ]

                img_rgb = self.visualizer.draw_status(
                    img_rgb,
                    status=str(self.state),
                    fish_count=self.stats.successful_catches,
                    audio_level=self.audio.get_current_level(),
                    extra_info=extra_info,
                    threshold=self.config.decibel_threshold
                )
                self.visualizer.show(img_rgb)

            time.sleep(0.1)

        # Try to detect bobber
        self._set_state(BotState.DETECTING_BOBBER)
        bobber_position = None
        bobber_confidence = None

        detection_start = time.time()
        max_detection_time = self.config.cast_duration_sec

        while (time.time() - detection_start) < max_detection_time:
            img, position, confidence = self.capture_and_detect()

            # Update visualization
            if self.visualizer and img is not None:
                extra_info = [
                    f"Cast: {self.stats.total_casts}",
                    f"Time: {int(time.time() - cast_start)}s"
                ]
                if confidence:
                    extra_info.append(f"Confidence: {confidence:.2%}")

                img = self.visualizer.draw_status(
                    img,
                    status=str(self.state),
                    fish_count=self.stats.successful_catches,
                    audio_level=self.audio.get_current_level(),
                    extra_info=extra_info,
                    threshold=self.config.decibel_threshold
                )
                self.visualizer.show(img)

            if position and confidence:
                bobber_position = position
                bobber_confidence = confidence
                self.logger.info(f"Bobber detected! Confidence: {confidence:.2%}")
                break

            time.sleep(self.config.detection_interval_sec)

        if not bobber_position:
            self.logger.warning("Could not detect bobber")
            self.stats.record_failed_cast()
            return False

        # Wait for fish to bite
        time_remaining = self.config.cast_duration_sec - (time.time() - detection_start)
        caught = self.wait_for_bite(bobber_position, max_duration=time_remaining, cast_start=cast_start)

        cast_duration = time.time() - cast_start

        if caught:
            self.stats.record_catch(cast_duration)
            self.logger.info(f"Fish caught! (Cast time: {cast_duration:.1f}s)")
        else:
            self.stats.record_failed_cast()
            self.logger.info("No fish this time")

        return caught

    def fishing_loop(self) -> None:
        """Main fishing loop."""
        self.running = True
        self._set_state(BotState.INITIALIZING)

        # Focus game window
        if not self.focus_game_window():
            self.logger.error("Cannot continue without game window focus")
            return

        # Start audio detector
        if not self.audio.start():
            self.logger.error("Failed to start audio detection")
            return

        self.logger.info("Starting fishing loop")

        try:
            while self.running:
                # Check if we need to apply lure
                if self.should_apply_lure():
                    self.apply_lure()

                # Perform fishing cast
                self.perform_cast()

                # Random delay before next cast (anti-detection) with visualization
                if self.running:
                    delay = random.uniform(
                        self.config.min_recast_delay_sec,
                        self.config.max_recast_delay_sec
                    )
                    if delay > 0:
                        self.logger.debug(f"Waiting {delay:.1f}s before next cast")
                        self._set_state(BotState.IDLE)

                        delay_start = time.time()
                        while time.time() - delay_start < delay and self.running:
                            if self.visualizer:
                                sct_img = self.sct.grab(self.monitor_dict)
                                img = np.array(sct_img)
                                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

                                remaining = delay - (time.time() - delay_start)
                                extra_info = [
                                    f"Total Casts: {self.stats.total_casts}",
                                    f"Success Rate: {self.stats.success_rate:.1f}%",
                                    f"Next cast in: {remaining:.1f}s"
                                ]

                                img_rgb = self.visualizer.draw_status(
                                    img_rgb,
                                    status=str(self.state),
                                    fish_count=self.stats.successful_catches,
                                    audio_level=self.audio.get_current_level(),
                                    extra_info=extra_info,
                                    threshold=self.config.decibel_threshold
                                )
                                self.visualizer.show(img_rgb)

                            time.sleep(0.1)

        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        except Exception as e:
            self.logger.error(f"Error in fishing loop: {e}", exc_info=True)
            self._set_state(BotState.ERROR)
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the bot and cleanup resources."""
        self.running = False
        self._set_state(BotState.STOPPED)

        self.logger.info("Stopping bot and cleaning up resources")

        # Stop audio
        self.audio.stop()

        # Close visualization
        if self.visualizer:
            self.visualizer.close()

        # Close screen capture
        try:
            self.sct.close()
        except Exception:
            pass

        # Print statistics
        print(self.stats.get_summary())

        self.logger.info("Bot stopped")

    def run(self) -> None:
        """Main entry point to run the bot."""
        self.show_banner()

        # Update config from user if needed
        if not self.config.fishing_key:
            self.config.update_from_user_input()

        # Start fishing
        self.fishing_loop()


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description="WoW Fishing Bot with YOLO Detection",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--config", "-c",
        type=str,
        default="config.json",
        help="Path to configuration file (default: config.json)"
    )
    parser.add_argument(
        "--live-view",
        action="store_true",
        help="Enable live visualization window"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with verbose logging"
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Path to YOLO model weights (overrides config)"
    )
    parser.add_argument(
        "--no-config-prompt",
        action="store_true",
        help="Skip configuration prompts, use existing config"
    )

    args = parser.parse_args()

    # Load configuration
    config = FishingConfig.load(args.config)

    # Apply command-line overrides
    if args.live_view:
        config.live_view = True
    if args.debug:
        config.debug = True
    if args.model:
        config.model_path = args.model

    # Prompt for config if fishing key not set (unless disabled)
    if not args.no_config_prompt and not config.fishing_key:
        config.update_from_user_input()

    # Create and run bot
    try:
        bot = WoWFisher(config)
        bot.run()
    except Exception as e:
        logger = get_logger()
        logger.critical(f"Fatal error: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
