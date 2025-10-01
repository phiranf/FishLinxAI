"""Configuration management for WoW Fisher bot."""

import json
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class FishingConfig:
    """Configuration for fishing bot."""

    # Keys
    fishing_key: str = "1"
    lure_key: Optional[str] = None
    lure_duration_minutes: int = 10

    # Detection settings
    model_path: str = "../runs/detect/train3/weights/best.pt"
    confidence_threshold: float = 0.5
    decibel_threshold: float = -45.0

    # Timing settings
    cast_duration_sec: int = 30
    detection_interval_sec: float = 2.0
    initial_wait_sec: float = 4.0
    audio_wait_sec: float = 2.0
    lure_apply_wait_sec: float = 5.0
    window_focus_wait_sec: float = 0.5

    # Randomization (anti-detection)
    min_recast_delay_sec: float = 0.0
    max_recast_delay_sec: float = 3.0

    # Audio settings
    audio_rate: int = 44100
    audio_chunk: int = 2048

    # Display settings
    game_window_name: str = "World of Warcraft"
    live_view: bool = False
    debug: bool = False

    # Visualization window settings
    viz_window_monitor: int = 2  # Which monitor to show viz window (1 = primary, 2 = secondary, etc.)
    viz_window_width: int = 1200
    viz_window_height: int = 800
    viz_window_x: Optional[int] = None  # Override X position (None = auto)
    viz_window_y: Optional[int] = None  # Override Y position (None = auto)
    viz_show_fps: bool = True
    viz_show_audio_graph: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FishingConfig':
        """Create config from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})

    def save(self, filepath: str = "config.json") -> None:
        """Save configuration to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=4)

    @classmethod
    def load(cls, filepath: str = "config.json") -> 'FishingConfig':
        """Load configuration from JSON file."""
        if not os.path.exists(filepath):
            return cls()

        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)

    def update_from_user_input(self) -> None:
        """Interactively update configuration from user input."""
        print("\n=== Fisher Bot Configuration ===")

        # Fishing key
        fishing_key = input(f"Fishing spell key [{self.fishing_key}]: ").strip().lower()
        if fishing_key:
            self.fishing_key = fishing_key

        # Lure settings
        use_lure = input(f"Use lure? (y/n) [{'y' if self.lure_key else 'n'}]: ").strip().lower()
        if use_lure == 'y':
            lure_key = input(f"Lure key [{self.lure_key or '2'}]: ").strip().lower()
            if lure_key:
                self.lure_key = lure_key
            elif not self.lure_key:
                self.lure_key = '2'

            duration = input(f"Lure duration in minutes [{self.lure_duration_minutes}]: ").strip()
            if duration:
                try:
                    self.lure_duration_minutes = int(duration)
                except ValueError:
                    print(f"Invalid duration, using default: {self.lure_duration_minutes}")
        elif use_lure == 'n':
            self.lure_key = None

        # Ask to save
        save_config = input("\nSave this configuration? (y/n) [y]: ").strip().lower()
        if save_config != 'n':
            self.save()
            print("Configuration saved to config.json")
