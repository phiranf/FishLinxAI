# monitor.py -- Linux (wmctrl / xwininfo) implementation
import subprocess
from typing import List, Optional, Tuple
from screeninfo import get_monitors
import pyautogui


def get_window_handle(window_name: str) -> List[str]:
    """
    Return list of window IDs (hex strings) that contain window_name (case-insensitive).
    Requires `wmctrl`.
    """
    try:
        result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, check=True)
    except FileNotFoundError:
        raise RuntimeError("wmctrl not found. Install it (e.g. sudo apt install wmctrl)")
    windows: List[str] = []
    for line in result.stdout.splitlines():
        # wmctrl -l output: <win_id> <desktop> <host?> <title...>
        parts = line.split(None, 3)
        if len(parts) == 4:
            win_id, _, _, title = parts
            if window_name.lower() in title.lower():
                windows.append(win_id)
    return windows


def get_window_rect(window_id: str) -> Optional[Tuple[int, int, int, int]]:
    """
    Return window rectangle as (left, top, right, bottom) for the given window_id.
    Uses xwininfo -id <window_id>.
    """
    try:
        result = subprocess.run(["xwininfo", "-id", window_id], capture_output=True, text=True, check=True)
    except FileNotFoundError:
        raise RuntimeError("xwininfo not found. Install it (e.g. sudo apt install x11-utils)")

    x = y = w = h = None
    for raw in result.stdout.splitlines():
        line = raw.strip()
        if line.startswith("Absolute upper-left X:"):
            try:
                x = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("Absolute upper-left Y:"):
            try:
                y = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("Width:"):
            try:
                w = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("Height:"):
            try:
                h = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass

    # If any value is still None, try some relaxed matching (locales / different xwininfo variants)
    if None in (x, y, w, h):
        for raw in result.stdout.splitlines():
            if "Upper-left X" in raw and x is None:
                try:
                    x = int(raw.split(":", 1)[1].strip())
                except Exception:
                    pass
            if "Upper-left Y" in raw and y is None:
                try:
                    y = int(raw.split(":", 1)[1].strip())
                except Exception:
                    pass

    if None in (x, y, w, h):
        return None

    return (x, y, x + w, y + h)


def find_monitor_for_window(window_name: str):
    """
    Find the monitor that contains the top-left of the first matching window.
    Returns (monitor, window_rect) where monitor is a screeninfo.Monitor object and
    window_rect is (left, top, right, bottom). If not found, returns (None, None) or (None, rect).
    """
    hwnd_list = get_window_handle(window_name)
    if not hwnd_list:
        return None, None

    hwnd = hwnd_list[0]
    window_rect = get_window_rect(hwnd)
    if not window_rect:
        return None, None

    for monitor in get_monitors():
        if (monitor.x <= window_rect[0] <= monitor.x + monitor.width and
                monitor.y <= window_rect[1] <= monitor.y + monitor.height):
            return monitor, window_rect
    return None, window_rect


def focus_window(game_name: str) -> bool:
    """
    Bring the first matching window to the foreground using wmctrl.
    Returns True if a window was found (regardless of whether focus succeeded).
    """
    hwnd_list = get_window_handle(game_name)
    if not hwnd_list:
        return False

    # Activate the window (wmctrl accepts hex id when using -i)
    try:
        subprocess.run(["wmctrl", "-i", "-a", hwnd_list[0]], check=False)
    except FileNotFoundError:
        raise RuntimeError("wmctrl not found. Install it (e.g. sudo apt install wmctrl)")

    # Fallback: small click inside the window to force focus on stubborn WMs
    rect = get_window_rect(hwnd_list[0])
    if rect:
        try:
            pyautogui.click(rect[0] + 10, rect[1] + 10)
        except Exception:
            # pyautogui may raise if DISPLAY not set or other issues; ignore fallback errors
            pass

    return True


def get_monitor_dict(game_name: str):
    """
    Return a dict with top/left/width/height describing the window's rectangle on its monitor,
    or None if the window or monitor can't be found.
    """
    monitor, rect = find_monitor_for_window(game_name)

    if monitor and rect:
        return {
            "top": rect[1],
            "left": rect[0],
            "width": rect[2] - rect[0],
            "height": rect[3] - rect[1]
        }
    else:
        return None
