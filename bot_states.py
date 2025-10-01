"""State management for fishing bot."""

from enum import Enum, auto


class BotState(Enum):
    """Enumeration of possible bot states."""

    IDLE = auto()
    INITIALIZING = auto()
    APPLYING_LURE = auto()
    CASTING = auto()
    DETECTING_BOBBER = auto()
    WAITING_FOR_BITE = auto()
    CATCHING = auto()
    LOOTING = auto()
    STOPPED = auto()
    ERROR = auto()

    def __str__(self) -> str:
        """Return human-readable state name."""
        return self.name.replace("_", " ")
