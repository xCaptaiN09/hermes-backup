#!/usr/bin/env python3
"""
Linux Computer Use - Screen Control v3.0
Pixel-perfect desktop automation via compositor socket + AT-SPI accessibility tree.

Key features:
  - click_element: Click UI elements BY NAME (no coordinates needed)
  - click: Click at exact pixel coordinates via compositor warp + native click
  - capture: Screenshot with window geometry
  - All pointer ops use compositor socket for pixel-perfect accuracy
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path


# ─── Compositor Socket IPC ────────────────────────────────────────────────────

SOCKET_PATH = "/tmp/hermes-hyprland.sock"

def send_socket_command(payload, socket_path=SOCKET_PATH):
    """Send JSON command to compositor socket and return response."""
    import socket as sock
    try:
        with sock.socket(sock.AF_UNIX, sock.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect(socket_path)
            s.sendall(json.dumps(payload).encode('utf-8'))
            response_data = b""
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                response_data += chunk
            return json.loads(response_data.decode('utf-8'))
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── Cursor & Window Queries ──────────────────────────────────────────────────

def get_cursor_pos():
    """Get current cursor position via hyprctl."""
    result = subprocess.run(["hyprctl", "cursorpos"], capture_output=True, text=True)
    if result.returncode == 0:
        parts = result.stdout.strip().split(",")
        return {"x": int(parts[0].strip()), "y": int(parts[1].strip())}
    return None


def get_windows():
    """Get all window positions via Hyprland plugin socket (compositor-level accuracy)."""
    try:
        import socket as sock
        s = sock.socket(sock.AF_UNIX, sock.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect(SOCKET_PATH)
        s.send(json.dumps({"action": "get_windows"}).encode())
        data = s.recv(65536).decode()
        s.close()
        result = json.loads(data)
        if result.get("success"):
            return result["windows"]
    except Exception:
        pass
    # fallback to hyprctl
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


# ─── Screenshot ───────────────────────────────────────────────────────────────

def take_screenshot(output_path="/tmp/hermes_screen.png", with_cursor=True):
    """Take screenshot using grimblast (includes cursor)."""
    if with_cursor:
        result = subprocess.run(
            ["grimblast", "save", "screen", output_path], capture_output=True, text=True
        )
    else:
        result = subprocess.run(["grim", output_path], capture_output=True, text=True)
    return result.returncode == 0


# ─── Mouse Movement ──────────────────────────────────────────────────────────

def move_mouse(x, y):
    """Move mouse to absolute coordinates using compositor socket (pixel-perfect)."""
    res = send_socket_command({"action": "move_cursor", "x": x, "y": y})
    if res.get("success"):
        return True

    # Fallback to ydotool (less accurate on Wayland)
    result = subprocess.run(
        ["ydotool", "mousemove", "--absolute", "-x", str(x), "-y", str(y)],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def move_mouse_smooth(target_x, target_y):
    """Move mouse smoothly to absolute coordinates with ease-in-out velocity profile.

    Generates natural Wayland motion events to guarantee hover states register
    correctly on sub-surfaces and toolbar elements.
    """
    start = get_cursor_pos()
    if not start:
        return move_mouse(target_x, target_y)

    start_x, start_y = start["x"], start["y"]
    dx = target_x - start_x
    dy = target_y - start_y
    distance = (dx**2 + dy**2)**0.5

    if distance < 15:
        return move_mouse(target_x, target_y)

    # 1 step per 30px, minimum 5 steps, maximum 20 steps
    steps = max(5, min(20, int(distance / 30)))
    step_delay = 0.005  # 5ms delay per step (extremely fast but smooth)

    for i in range(1, steps + 1):
        t = i / steps
        # Quadratic ease-in-out interpolation
        if t < 0.5:
            factor = 2 * t * t
        else:
            factor = -1 + (4 - 2 * t) * t

        x = int(start_x + dx * factor)
        y = int(start_y + dy * factor)

        move_mouse(x, y)
        time.sleep(step_delay)

    # Ensure final warp reaches absolute destination
    return move_mouse(target_x, target_y)


# ─── Click at Coordinates ────────────────────────────────────────────────────

def click(x=None, y=None, button="left", window_index=None, windows=None):
    """Click at exact pixel coordinates using smooth mouse move + ydotool click.

    Strategy: Smooth ease-in-out cursor movement generates correct pointer motion
    events so toolkits (GTK, Qt) properly register mouse enter/hover states,
    then ydotool click goes through kernel input layer to execute the click.
    """
    if window_index and windows:
        win = next((w for w in windows if w["index"] == window_index), None)
        if win:
            x, y = win["center_x"], win["center_y"]

    if x is None or y is None:
        return False

    # 1. Move cursor smoothly to target position
    moved = move_mouse_smooth(x, y)
    if not moved:
        return False

    # Wait for compositor/client to process hover transition
    time.sleep(0.15)

    # 2. Click via ydotool (kernel input layer — properly received by GTK/Qt)
    button_code = {"left": "0xC0", "right": "0xC8", "middle": "0xC4"}.get(
        button, "0xC0"
    )
    result = subprocess.run(
        ["ydotool", "click", button_code], capture_output=True, text=True
    )
    time.sleep(0.15)
    return result.returncode == 0


# ─── AT-SPI Element Discovery ────────────────────────────────────────────────

def _find_atspi_element(app_class, element_name, role_hint=None):
    """Search AT-SPI accessibility tree for element by name. Returns (abs_x, abs_y) center or None.

    Uses GObject Introspection (gi.repository.Atspi) for reliable element discovery.
    Fuses AT-SPI window-relative bounds with compositor window geometry for absolute coords.
    """
    try:
        import gi
        gi.require_version('Atspi', '2.0')
        from gi.repository import Atspi
    except Exception:
        return None

    # Get compositor window geometry for absolute coordinate calculation
    windows = get_windows()
    target_win = None
    if app_class:
        app_lower = app_class.lower()
        for w in windows:
            if app_lower in w.get("class", "").lower() or app_lower in w.get("title", "").lower():
                target_win = w
                break
    if not target_win:
        # Use focused window
        for w in windows:
            if w.get("focused"):
                target_win = w
                break
    if not target_win and windows:
        target_win = windows[0]
    if not target_win:
        return None

    win_x = target_win["x"]
    win_y = target_win["y"]
    win_class = target_win.get("class", "")

    # Find matching AT-SPI application
    desktop = Atspi.get_desktop(0)
    atspi_app = None
    for i in range(desktop.get_child_count()):
        child = desktop.get_child_at_index(i)
        if child:
            child_name = child.get_name() or ""
            if (win_class.lower() in child_name.lower() or
                child_name.lower() in win_class.lower()):
                atspi_app = child
                break

    if not atspi_app:
        return None

    # Recursive search for element by name
    name_lower = element_name.lower()
    best_match = None
    best_score = 0

    def search_tree(node, depth=0):
        nonlocal best_match, best_score
        if depth > 15:  # Prevent infinite recursion
            return
        try:
            node_name = (node.get_name() or "").strip()
            node_role = (node.get_role_name() or "").strip()

            if node_name:
                name_l = node_name.lower()
                score = 0

                # Exact match is best
                if name_l == name_lower:
                    score = 100
                # Starts with
                elif name_l.startswith(name_lower) or name_lower.startswith(name_l):
                    score = 80
                # Contains
                elif name_lower in name_l or name_l in name_lower:
                    score = 60

                # Bonus for matching role hint
                if role_hint and role_hint.lower() in node_role.lower():
                    score += 20

                # Bonus for interactive roles (buttons, menu items, etc.)
                interactive_roles = {"push button", "toggle button", "menu item",
                                     "tool bar button", "link", "check box",
                                     "radio button", "combo box", "entry",
                                     "page tab"}
                if node_role.lower() in interactive_roles:
                    score += 10

                if score > best_score:
                    # Get bounds using WINDOW coords (type 1) then add compositor offset
                    # On Wayland, SCREEN coords (type 0) are unreliable because apps
                    # don't know their absolute screen position. So we use WINDOW-relative
                    # coords and add the compositor's window x,y for true screen position.
                    try:
                        rect = node.get_extents(1)  # 1 = WINDOW-relative coords
                        if rect.width > 0 and rect.height > 0 and rect.x > -10000 and rect.y > -10000:
                            abs_x = win_x + rect.x
                            abs_y = win_y + rect.y
                            best_score = score
                            best_match = {
                                "name": node_name,
                                "role": node_role,
                                "x": abs_x + rect.width // 2,
                                "y": abs_y + rect.height // 2,
                                "bounds": {
                                    "x": abs_x, "y": abs_y,
                                    "width": rect.width, "height": rect.height
                                }
                            }
                    except Exception:
                        pass

            # Recurse into children
            child_count = node.get_child_count()
            for i in range(child_count):
                child = node.get_child_at_index(i)
                if child:
                    search_tree(child, depth + 1)
        except Exception:
            pass

    search_tree(atspi_app)
    return best_match


def click_element(app_class, element_name, button="left", role_hint=None):
    """Click a UI element by its accessible name. Resolution-independent.

    This searches the AT-SPI accessibility tree for an element matching
    `element_name` within the window matching `app_class`, then clicks
    its center using compositor-native pixel-perfect coordinates.

    Works regardless of window size, position, or screen resolution.
    """
    match = _find_atspi_element(app_class, element_name, role_hint)
    if not match:
        return {"success": False, "error": f"Element '{element_name}' not found in '{app_class}'"}

    # Click at the element's absolute center
    # Compositor warp positions cursor on target surface, ydotool delivers click
    # No need to focus_window — cursor position determines click target on Wayland
    success = click(x=match["x"], y=match["y"], button=button)
    return {
        "success": success,
        "element": match["name"],
        "role": match["role"],
        "clicked_at": {"x": match["x"], "y": match["y"]},
        "bounds": match["bounds"]
    }


def list_elements(app_class):
    """List all accessible UI elements in a window. Useful for discovering element names."""
    try:
        import gi
        gi.require_version('Atspi', '2.0')
        from gi.repository import Atspi
    except Exception:
        return {"success": False, "error": "AT-SPI not available"}

    windows = get_windows()
    target_win = None
    if app_class:
        app_lower = app_class.lower()
        for w in windows:
            if app_lower in w.get("class", "").lower() or app_lower in w.get("title", "").lower():
                target_win = w
                break
    if not target_win:
        for w in windows:
            if w.get("focused"):
                target_win = w
                break
    if not target_win and windows:
        target_win = windows[0]
    if not target_win:
        return {"success": False, "error": "No windows found"}

    win_class = target_win.get("class", "")
    win_x = target_win.get("x", 0)
    win_y = target_win.get("y", 0)

    desktop = Atspi.get_desktop(0)
    atspi_app = None
    for i in range(desktop.get_child_count()):
        child = desktop.get_child_at_index(i)
        if child:
            child_name = child.get_name() or ""
            if (win_class.lower() in child_name.lower() or
                child_name.lower() in win_class.lower()):
                atspi_app = child
                break

    if not atspi_app:
        return {"success": False, "error": f"No AT-SPI app matches '{app_class}'"}

    elements = []

    def collect(node, depth=0):
        if depth > 10 or len(elements) >= 100:
            return
        try:
            name = (node.get_name() or "").strip()
            role = (node.get_role_name() or "").strip()
            if name and role:
                rect = node.get_extents(1)  # WINDOW-relative coords
                if rect.width > 0 and rect.height > 0 and rect.x > -10000 and rect.y > -10000:
                    elements.append({
                        "name": name,
                        "role": role,
                        "center_x": win_x + rect.x + rect.width // 2,
                        "center_y": win_y + rect.y + rect.height // 2,
                    })
            child_count = node.get_child_count()
            for i in range(child_count):
                child = node.get_child_at_index(i)
                if child:
                    collect(child, depth + 1)
        except Exception:
            pass

    collect(atspi_app)
    return {"success": True, "app": win_class, "elements": elements, "count": len(elements)}


# ─── Keyboard Input ──────────────────────────────────────────────────────────

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


# ─── Window Focus ────────────────────────────────────────────────────────────

def focus_window(class_name=None, title=None):
    """Focus a window by class or title."""
    if class_name:
        subprocess.run(["hyprctl", "dispatch", "focuswindow", f"class:{class_name}"],
                       capture_output=True)
    elif title:
        subprocess.run(["hyprctl", "dispatch", "focuswindow", f"title:{title}"],
                       capture_output=True)


# ─── Capture ─────────────────────────────────────────────────────────────────

def capture(mode="full", app=None, output=None):
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
        "instructions": "Use 'click_element <app_class> <element_name>' to click buttons/menus by name (recommended), or 'click <x> <y>' for exact coordinates.",
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


# ─── CLI Entry Point ─────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: screen_control.py <action> [args]", "actions": [
            "capture [app]", "windows", "cursor",
            "click <x> <y> [button]",
            "click_element <app_class> <element_name> [button]",
            "list_elements <app_class>",
            "move <x> <y>", "type <text>", "key <combo>", "focus <class>"
        ]}))
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

    elif action == "click_element":
        app_class = sys.argv[2]
        element_name = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
        if not element_name:
            print(json.dumps({"error": "Usage: click_element <app_class> <element_name>"}))
            return
        result = click_element(app_class, element_name)
        print(json.dumps(result, indent=2))

    elif action == "list_elements":
        app_class = sys.argv[2] if len(sys.argv) > 2 else None
        result = list_elements(app_class)
        print(json.dumps(result, indent=2))

    elif action == "move":
        x, y = int(sys.argv[2]), int(sys.argv[3])
        success = move_mouse_smooth(x, y)
        print(json.dumps({"success": success, "x": x, "y": y}))

    elif action == "type":
        text = " ".join(sys.argv[2:])
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

    else:
        print(json.dumps({"error": f"Unknown action: {action}"}))


if __name__ == "__main__":
    main()
