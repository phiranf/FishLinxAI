"""Statistics tracking for fishing sessions."""

import time
from dataclasses import dataclass, field
from typing import List
from datetime import datetime, timedelta


@dataclass
class FishingStatistics:
    """Track fishing session statistics."""

    session_start: float = field(default_factory=time.time)
    total_casts: int = 0
    successful_catches: int = 0
    failed_casts: int = 0
    total_detections: int = 0
    detection_failures: int = 0

    # Timing stats
    cast_times: List[float] = field(default_factory=list)

    def record_cast(self) -> None:
        """Record a fishing cast."""
        self.total_casts += 1

    def record_catch(self, cast_duration: float) -> None:
        """
        Record a successful catch.

        Args:
            cast_duration: Time taken for this cast in seconds
        """
        self.successful_catches += 1
        self.cast_times.append(cast_duration)

    def record_failed_cast(self) -> None:
        """Record a failed cast (no fish caught)."""
        self.failed_casts += 1

    def record_detection(self, success: bool) -> None:
        """
        Record a bobber detection attempt.

        Args:
            success: Whether the bobber was detected
        """
        if success:
            self.total_detections += 1
        else:
            self.detection_failures += 1

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_casts == 0:
            return 0.0
        return (self.successful_catches / self.total_casts) * 100

    @property
    def detection_rate(self) -> float:
        """Calculate detection success rate as percentage."""
        total_attempts = self.total_detections + self.detection_failures
        if total_attempts == 0:
            return 0.0
        return (self.total_detections / total_attempts) * 100

    @property
    def average_cast_time(self) -> float:
        """Calculate average time per successful cast."""
        if not self.cast_times:
            return 0.0
        return sum(self.cast_times) / len(self.cast_times)

    @property
    def session_duration(self) -> float:
        """Get session duration in seconds."""
        return time.time() - self.session_start

    @property
    def fish_per_hour(self) -> float:
        """Calculate fish caught per hour."""
        hours = self.session_duration / 3600
        if hours == 0:
            return 0.0
        return self.successful_catches / hours

    def get_summary(self) -> str:
        """
        Get formatted statistics summary.

        Returns:
            Multi-line string with session statistics
        """
        duration = timedelta(seconds=int(self.session_duration))

        summary = [
            "\n" + "=" * 50,
            "FISHING SESSION STATISTICS",
            "=" * 50,
            f"Session Duration:    {duration}",
            f"Total Casts:         {self.total_casts}",
            f"Fish Caught:         {self.successful_catches}",
            f"Failed Casts:        {self.failed_casts}",
            f"Success Rate:        {self.success_rate:.1f}%",
            "",
            f"Bobber Detected:     {self.total_detections}",
            f"Detection Failed:    {self.detection_failures}",
            f"Detection Rate:      {self.detection_rate:.1f}%",
            "",
            f"Avg Cast Time:       {self.average_cast_time:.1f}s",
            f"Fish per Hour:       {self.fish_per_hour:.1f}",
            "=" * 50,
        ]

        return "\n".join(summary)

    def reset(self) -> None:
        """Reset all statistics."""
        self.session_start = time.time()
        self.total_casts = 0
        self.successful_catches = 0
        self.failed_casts = 0
        self.total_detections = 0
        self.detection_failures = 0
        self.cast_times.clear()
