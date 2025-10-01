"""Visualization handler for live detection display."""

import cv2
import numpy as np
import time
from typing import Optional, Tuple, List, Deque
from collections import deque
from screeninfo import get_monitors
from logger import get_logger


class VisualizationHandler:
    """Handles live visualization of YOLO detections and bot status."""

    def __init__(
        self,
        window_name: str = "WoW Fisher - Live View",
        enabled: bool = True,
        monitor_id: int = 2,
        width: int = 1200,
        height: int = 800,
        x_pos: Optional[int] = None,
        y_pos: Optional[int] = None,
        show_fps: bool = True,
        show_audio_graph: bool = True
    ):
        """
        Initialize visualization handler.

        Args:
            window_name: Name of the OpenCV window
            enabled: Whether visualization is enabled
            monitor_id: Which monitor to display on (1=primary, 2=secondary, etc.)
            width: Window width in pixels
            height: Window height in pixels
            x_pos: Override X position (None = auto-calculate for monitor)
            y_pos: Override Y position (None = auto-calculate for monitor)
            show_fps: Show FPS counter
            show_audio_graph: Show audio level graph
        """
        self.window_name = window_name
        self.enabled = enabled
        self.logger = get_logger()
        self.show_fps = show_fps
        self.show_audio_graph = show_audio_graph

        # FPS tracking
        self.frame_times: Deque[float] = deque(maxlen=30)
        self.last_frame_time = time.time()

        # Audio level history for graph
        self.audio_history: Deque[float] = deque(maxlen=100)

        if not self.enabled:
            return

        # Create window
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, width, height)

        # Position window on specified monitor
        try:
            monitors = list(get_monitors())
            if len(monitors) >= monitor_id:
                target_monitor = monitors[monitor_id - 1]

                if x_pos is None or y_pos is None:
                    # Auto-calculate position to center on target monitor
                    x_pos = target_monitor.x + (target_monitor.width - width) // 2
                    y_pos = target_monitor.y + (target_monitor.height - height) // 2

                cv2.moveWindow(self.window_name, x_pos, y_pos)
                self.logger.info(
                    f"Visualization window created on monitor {monitor_id} "
                    f"at ({x_pos}, {y_pos}) - {width}x{height}"
                )
            else:
                self.logger.warning(
                    f"Monitor {monitor_id} not found. Found {len(monitors)} monitors. "
                    f"Using default position."
                )
        except Exception as e:
            self.logger.warning(f"Could not position window on monitor {monitor_id}: {e}")

        self.logger.debug(f"Visualization window '{window_name}' created")

    def _calculate_fps(self) -> float:
        """Calculate current FPS."""
        current_time = time.time()
        frame_time = current_time - self.last_frame_time
        self.last_frame_time = current_time
        self.frame_times.append(frame_time)

        if len(self.frame_times) > 0:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            return 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0
        return 0.0

    def draw_detection(
        self,
        image: np.ndarray,
        bbox: Tuple[int, int, int, int],
        confidence: float,
        center: Optional[Tuple[int, int]] = None
    ) -> np.ndarray:
        """
        Draw bounding box and detection info on image.

        Args:
            image: Image to draw on
            bbox: Bounding box coordinates (x1, y1, x2, y2)
            confidence: Detection confidence score
            center: Optional center point to highlight

        Returns:
            Image with drawings
        """
        x1, y1, x2, y2 = bbox

        # Draw bounding box with glow effect
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 3)
        cv2.rectangle(image, (x1-1, y1-1), (x2+1, y2+1), (0, 200, 0), 1)

        # Draw center point with crosshair
        if center:
            cx, cy = center
            # Center dot
            cv2.circle(image, center, 6, (0, 0, 255), -1)
            cv2.circle(image, center, 8, (255, 255, 255), 2)
            # Crosshair
            cv2.line(image, (cx - 20, cy), (cx + 20, cy), (0, 0, 255), 2)
            cv2.line(image, (cx, cy - 20), (cx, cy + 20), (0, 0, 255), 2)

        # Draw confidence score with background
        conf_text = f"Bobber: {confidence:.1%}"
        (text_w, text_h), _ = cv2.getTextSize(conf_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.rectangle(image, (x1, y1 - text_h - 15), (x1 + text_w + 10, y1), (0, 255, 0), -1)
        cv2.putText(
            image, conf_text, (x1 + 5, y1 - 8),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2
        )

        # Draw bbox dimensions
        bbox_w = x2 - x1
        bbox_h = y2 - y1
        dim_text = f"{bbox_w}x{bbox_h}px"
        cv2.putText(
            image, dim_text, (x1, y2 + 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1
        )

        return image

    def draw_audio_graph(
        self,
        image: np.ndarray,
        current_level: Optional[float],
        threshold: float = -45.0
    ) -> np.ndarray:
        """
        Draw audio level graph.

        Args:
            image: Image to draw on
            current_level: Current audio level in dB
            threshold: Detection threshold

        Returns:
            Image with audio graph
        """
        if not self.show_audio_graph:
            return image

        # Add current level to history
        if current_level is not None:
            self.audio_history.append(current_level)

        if len(self.audio_history) == 0:
            return image

        h, w = image.shape[:2]
        graph_height = 150
        graph_width = 300
        graph_x = w - graph_width - 20
        graph_y = h - graph_height - 20

        # Draw graph background
        overlay = image.copy()
        cv2.rectangle(overlay, (graph_x, graph_y), (graph_x + graph_width, graph_y + graph_height), (0, 0, 0), -1)
        image = cv2.addWeighted(overlay, 0.5, image, 0.5, 0)

        # Draw border
        cv2.rectangle(image, (graph_x, graph_y), (graph_x + graph_width, graph_y + graph_height), (100, 100, 100), 2)

        # Draw threshold line
        threshold_y = graph_y + int((1 - (threshold + 100) / 100) * graph_height)
        cv2.line(image, (graph_x, threshold_y), (graph_x + graph_width, threshold_y), (0, 0, 255), 1)
        cv2.putText(image, f"Threshold: {threshold}dB", (graph_x + 5, threshold_y - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        # Draw audio levels
        if len(self.audio_history) > 1:
            points = []
            for i, level in enumerate(self.audio_history):
                x = graph_x + int((i / (len(self.audio_history) - 1)) * (graph_width - 1))
                # Map -100dB to 0dB range to graph height
                normalized = (level + 100) / 100
                y = graph_y + int((1 - normalized) * graph_height)
                points.append((x, y))

            # Draw line graph
            for i in range(len(points) - 1):
                color = (0, 255, 0) if self.audio_history[i] > threshold else (100, 100, 100)
                cv2.line(image, points[i], points[i + 1], color, 2)

        # Draw current level indicator
        if current_level is not None:
            level_text = f"Audio: {current_level:.1f} dB"
            color = (0, 255, 0) if current_level > threshold else (100, 100, 100)
            cv2.putText(image, level_text, (graph_x + 5, graph_y + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        return image

    def draw_status(
        self,
        image: np.ndarray,
        status: str,
        fish_count: int,
        audio_level: Optional[float] = None,
        extra_info: Optional[List[str]] = None,
        threshold: float = -45.0
    ) -> np.ndarray:
        """
        Draw status information on image.

        Args:
            image: Image to draw on
            status: Current bot status
            fish_count: Number of fish caught
            audio_level: Current audio level in dB
            extra_info: Additional lines of info to display
            threshold: Audio detection threshold

        Returns:
            Image with status overlay
        """
        y_offset = 35
        line_height = 35

        # Calculate FPS
        fps = self._calculate_fps() if self.show_fps else 0

        # Calculate background height
        info_lines = len(extra_info or [])
        bg_height = 120 + (info_lines * (line_height - 5))
        if self.show_fps:
            bg_height += line_height

        # Draw semi-transparent background for better readability
        overlay = image.copy()
        cv2.rectangle(overlay, (10, 10), (450, bg_height), (0, 0, 0), -1)
        image = cv2.addWeighted(overlay, 0.6, image, 0.4, 0)

        # Draw border
        cv2.rectangle(image, (10, 10), (450, bg_height), (50, 50, 50), 2)

        # Title
        cv2.putText(
            image, "WoW Fisher - Live View", (20, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2
        )
        y_offset += line_height

        # Status with color coding
        status_colors = {
            "IDLE": (128, 128, 128),
            "CASTING": (255, 255, 0),
            "DETECTING_BOBBER": (255, 165, 0),
            "WAITING_FOR_BITE": (0, 255, 255),
            "CATCHING": (0, 255, 0),
            "LOOTING": (0, 200, 0),
        }
        status_color = status_colors.get(status, (128, 128, 128))
        cv2.putText(
            image, f"Status: {status}", (20, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2
        )
        y_offset += line_height

        # Fish count
        cv2.putText(
            image, f"Fish Caught: {fish_count}", (20, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
        )
        y_offset += line_height

        # FPS
        if self.show_fps:
            fps_color = (0, 255, 0) if fps > 5 else (0, 165, 255) if fps > 2 else (0, 0, 255)
            cv2.putText(
                image, f"FPS: {fps:.1f}", (20, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, fps_color, 2
            )
            y_offset += line_height

        # Extra info
        if extra_info:
            for info in extra_info:
                cv2.putText(
                    image, info, (20, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1
                )
                y_offset += 30

        # Draw audio graph
        image = self.draw_audio_graph(image, audio_level, threshold)

        return image

    def show(self, image: np.ndarray) -> None:
        """
        Display image in window.

        Args:
            image: Image to display
        """
        if not self.enabled:
            return

        cv2.imshow(self.window_name, image)
        cv2.waitKey(1)

    def close(self) -> None:
        """Close visualization window."""
        if self.enabled:
            cv2.destroyWindow(self.window_name)
            self.logger.debug(f"Visualization window '{self.window_name}' closed")

    def is_window_open(self) -> bool:
        """
        Check if window is still open.

        Returns:
            True if window is open, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Try to get window property - will fail if window is closed
            return cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) >= 0
        except Exception:
            return False
