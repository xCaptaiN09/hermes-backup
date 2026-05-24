#!/usr/bin/env python3
"""
Linux Computer Use - Screen Control
Works like macOS SOM: captures screen, indexes clickable elements,
returns numbered overlay for Hermes to click by index.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def get_cursor_pos():
    """Get current cursor position via hyprctl."""
    result = subprocess.run(["hyprctl", "cursorpos"], capture_output=True, text=True)
    if result.returncode == 0:
        parts = result.stdout.strip().split(",")
        return {"x": int(parts[0].strip()), "y": int(parts[1].strip())}
    return None


def get_windows():
    """Get all window positions and sizes via hyprctl."""
    result = subprocess.run(
        ["hyprctl", "clients", "-j"], capture_output=True, text=True
    )
    if result.returncode == 0:
        clients = json.loads(result.stdout)
        windows = []
        for c in clients:
            windows.append(
                {
                    "index": len(windows) + 1,
                    "class": c.get("class", ""),
                    "title": c.get("title", "")[:50],
                    "x": c["at"][0],
                    "y": c["at"][1],
                    "width": c["size"][0],
                    "height": c["size"][1],
                    "workspace": c.get("workspace", {}).get("id", 0),
                    "center_x": c["at"][0] + c["size"][0] // 2,
                    "center_y": c["at"][1] + c["size"][1] // 2,
                }
            )
        return windows
    return []


def get_atspi_elements(app_name=None):
    """Get accessible elements via AT-SPI for GTK/Qt apps."""
    try:
        import ctypes
        import ctypes.util

        atspi = ctypes.CDLL("libatspi.so.0")
        atspi.atspi_init()

        # Basic AT-SPI query - get desktop
        desktop = atspi.atspi_get_desktop(0)
        if not desktop:
            return []

        elements = []
        child_count = atspi.atspi_accessible_get_child_count(desktop, None)

        for i in range(min(child_count, 20)):
            child = atspi.atspi_accessible_get_child_at_index(desktop, i, None)
            if child:
                elements.append({"type": "atspi", "index": i})

        return elements
    except Exception as e:
        return []


def take_screenshot(output_path="/tmp/hermes_screen.png", with_cursor=True):
    """Take screenshot using grimblast (includes cursor)."""
    if with_cursor:
        result = subprocess.run(
            ["grimblast", "save", "screen", output_path], capture_output=True, text=True
        )
    else:
        result = subprocess.run(["grim", output_path], capture_output=True, text=True)
    return result.returncode == 0


def move_mouse(x, y):
    """Move mouse to absolute coordinates."""
    result = subprocess.run(
        ["ydotool", "mousemove", "--absolute", "-x", str(x), "-y", str(y)],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def click(x=None, y=None, button="left", window_index=None, windows=None):
    """Click at coordinates or window center."""
    if window_index and windows:
        win = next((w for w in windows if w["index"] == window_index), None)
        if win:
            x, y = win["center_x"], win["center_y"]

    if x is None or y is None:
        return False

    move_mouse(x, y)

    button_code = {"left": "0xC0", "right": "0xC8", "middle": "0xC4"}.get(
        button, "0xC0"
    )
    result = subprocess.run(
        ["ydotool", "click", button_code], capture_output=True, text=True
    )
    return result.returncode == 0


def type_text(text):
    """Type text at current cursor position."""
    result = subprocess.run(
        ["ydotool", "type", "--", text], capture_output=True, text=True
    )
    return result.returncode == 0


def key(keys):
    """Press key combination. e.g. 'ctrl+c', 'return', 'escape'"""
    key_map = {
        "return": "28:1 28:0",
        "escape": "1:1 1:0",
        "tab": "15:1 15:0",
        "space": "57:1 57:0",
        "ctrl+c": "29:1 46:1 46:0 29:0",
        "ctrl+v": "29:1 47:1 47:0 29:0",
        "ctrl+z": "29:1 44:1 44:0 29:0",
        "ctrl+s": "29:1 31:1 31:0 29:0",
        "ctrl+a": "29:1 30:1 30:0 29:0",
        "super": "125:1 125:0",
    }
    key_str = key_map.get(keys.lower(), "")
    if not key_str:
        return False
    result = subprocess.run(
        ["ydotool", "key"] + key_str.split(), capture_output=True, text=True
    )
    return result.returncode == 0


def focus_window(class_name=None, title=None):
    """Focus a window by class or title."""
    if class_name:
        subprocess.run(["hyprctl", "dispatch", "focuswindow", f"class:{class_name}"])
    elif title:
        subprocess.run(["hyprctl", "dispatch", "focuswindow", f"title:{title}"])


def capture(mode="full", app=None, output=None):
    import time

    if output is None:
        output = f"/tmp/hermes_screen_{int(time.time())}.png"
    """
    Main capture function - like macOS computer_use capture.
    Returns screenshot path + window index.
    """
    take_screenshot(output)
    windows = get_windows()
    cursor = get_cursor_pos()

    result = {
        "screenshot": output,
        "cursor": cursor,
        "windows": windows,
        "instructions": "Use window index to click window centers, or provide exact x,y coordinates.",
    }

    if app:
        matching = [
            w
            for w in windows
            if app.lower() in w["class"].lower() or app.lower() in w["title"].lower()
        ]
        result["target_windows"] = matching

    print(json.dumps(result, indent=2))
    return result


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: screen_control.py <action> [args]"}))
        return

    action = sys.argv[1]

    if action == "capture":
        app = sys.argv[2] if len(sys.argv) > 2 else None
        capture(app=app)

    elif action == "windows":
        print(json.dumps(get_windows(), indent=2))

    elif action == "cursor":
        print(json.dumps(get_cursor_pos()))

    elif action == "click":
        x, y = int(sys.argv[2]), int(sys.argv[3])
        button = sys.argv[4] if len(sys.argv) > 4 else "left"
        success = click(x=x, y=y, button=button)
        print(json.dumps({"success": success, "x": x, "y": y}))

    elif action == "move":
        x, y = int(sys.argv[2]), int(sys.argv[3])
        success = move_mouse(x, y)
        print(json.dumps({"success": success, "x": x, "y": y}))

    elif action == "type":
        text = sys.argv[2]
        success = type_text(text)
        print(json.dumps({"success": success}))

    elif action == "key":
        keys = sys.argv[2]
        success = key(keys)
        print(json.dumps({"success": success}))

    elif action == "focus":
        class_name = sys.argv[2] if len(sys.argv) > 2 else None
        focus_window(class_name=class_name)
        print(json.dumps({"success": True}))


if __name__ == "__main__":
    main()
