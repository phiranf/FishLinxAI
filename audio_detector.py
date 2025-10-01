"""Audio detection module for detecting fish splash sounds."""

import time
import numpy as np
import pyaudio
from typing import Optional, Tuple
from logger import get_logger


class AudioDetector:
    """Handles audio stream monitoring for fish splash detection."""

    def __init__(self, rate: int = 44100, chunk_size: int = 2048, threshold_db: float = -45.0):
        """
        Initialize audio detector.

        Args:
            rate: Audio sampling rate
            chunk_size: Audio buffer size
            threshold_db: Decibel threshold for splash detection
        """
        self.rate = rate
        self.chunk_size = chunk_size
        self.threshold_db = threshold_db
        self.logger = get_logger()

        self._audio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

    def start(self) -> bool:
        """
        Start audio stream.

        Returns:
            True if successful, False otherwise
        """
        try:
            self._audio = pyaudio.PyAudio()
            self._stream = self._audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk_size,
            )
            self.logger.debug("Audio stream started")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start audio stream: {e}")
            self._cleanup()
            return False

    def stop(self) -> None:
        """Stop and cleanup audio stream."""
        self._cleanup()
        self.logger.debug("Audio stream stopped")

    def _cleanup(self) -> None:
        """Internal cleanup method."""
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if self._audio:
            try:
                self._audio.terminate()
            except Exception:
                pass
            self._audio = None

    def listen_for_splash(self, max_duration: float, initial_delay: float = 2.0) -> Tuple[bool, Optional[float]]:
        """
        Listen for fish splash sound.

        Args:
            max_duration: Maximum time to listen (seconds)
            initial_delay: Initial delay before starting detection (seconds)

        Returns:
            Tuple of (detected: bool, decibel_level: Optional[float])
        """
        if not self._stream:
            self.logger.error("Audio stream not initialized")
            return False, None

        start_time = time.time()
        time.sleep(initial_delay)

        try:
            while time.time() - start_time < max_duration:
                try:
                    data = self._stream.read(self.chunk_size, exception_on_overflow=False)
                except Exception as e:
                    self.logger.warning(f"Audio read error: {e}")
                    break

                # Convert to normalized float samples
                samples = np.frombuffer(data, dtype=np.int16) / 32768.0
                if samples.size == 0:
                    continue

                # Calculate RMS and convert to decibels
                rms = np.sqrt(np.mean(samples ** 2))
                db = float(20 * np.log10(rms + 1e-6))

                if db > self.threshold_db:
                    self.logger.info(f"Splash detected! ({db:.1f} dB > {self.threshold_db:.1f} dB)")
                    return True, db

            return False, None

        except Exception as e:
            self.logger.error(f"Error during audio detection: {e}")
            return False, None

    def get_current_level(self) -> Optional[float]:
        """
        Get current audio level without blocking.

        Returns:
            Current decibel level or None if error
        """
        if not self._stream:
            return None

        try:
            data = self._stream.read(self.chunk_size, exception_on_overflow=False)
            samples = np.frombuffer(data, dtype=np.int16) / 32768.0
            if samples.size == 0:
                return None

            rms = np.sqrt(np.mean(samples ** 2))
            db = float(20 * np.log10(rms + 1e-6))
            return db
        except Exception:
            return None

    def is_active(self) -> bool:
        """Check if audio stream is active."""
        return self._stream is not None and self._stream.is_active()
