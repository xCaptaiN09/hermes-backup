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
    success = move_mouse(target_x, target_y)

    # Kernel-level relative nudge to force hover/enter highlight update in GTK/Qt
    try:
        subprocess.run(["ydotool", "mousemove", "--", "1", "1"], capture_output=True)
        subprocess.run(["ydotool", "mousemove", "--", "-1", "-1"], capture_output=True)
    except Exception:
        pass

    return success


# ─── Click at Coordinates ────────────────────────────────────────────────────

def click(x=None, y=None, button="left", click_count=1, window_index=None, windows=None):
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
    
    success = True
    for _ in range(click_count):
        result = subprocess.run(
            ["ydotool", "click", button_code], capture_output=True, text=True
        )
        if result.returncode != 0:
            success = False
        time.sleep(0.05)  # Safe double-click / multi-click interval
        
    time.sleep(0.15)
    return success


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
        if depth > 20:  # Deep enough to reach Thunar's detailed list view items (depth 12)
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

                # CRITICAL: Only apply interactive bonuses/penalties and consider a match
                # if there is a non-zero base name match. This avoids false matches on unrelated elements.
                if score > 0:
                    # Bonus for matching role hint
                    if role_hint and role_hint.lower() in node_role.lower():
                        score += 20

                    # Bonus for interactive and main-pane roles (buttons, menu items, table cells, icons)
                    interactive_roles = {"push button", "toggle button", "menu item",
                                         "tool bar button", "link", "check box",
                                         "radio button", "combo box", "entry",
                                         "page tab", "table cell", "list item", "icon"}
                    if node_role.lower() in interactive_roles:
                        score += 15

                    # Aggressive penalties for status/info bars to avoid misclicks in Thunar
                    penalized_roles = {"status bar", "info bar", "tool bar", "menu bar", "scroll bar"}
                    if node_role.lower() in penalized_roles:
                        score -= 50

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
def _get_thunar_view_mode(atspi_app):
    """Find the directory pane in Thunar and return its view mode name, or None."""
    def find_pane(node, depth=0):
        if not node or depth > 20:
            return None
        try:
            role = (node.get_role_name() or "").strip().lower()
            if role == "directory pane":
                return (node.get_name() or "").strip()
            for i in range(node.get_child_count()):
                res = find_pane(node.get_child_at_index(i), depth + 1)
                if res:
                    return res
        except Exception:
            pass
        return None
    return find_pane(atspi_app)


def _ensure_details_view(app_class):
    """If app is Thunar, check its view mode. If not Details view, focus, switch to Details, 
    and return the original view mode shortcut so it can be restored.
    """
    if not app_class or "thunar" not in app_class.lower():
        return None
        
    try:
        import gi
        gi.require_version('Atspi', '2.0')
        from gi.repository import Atspi
    except Exception:
        return None
        
    windows = get_windows()
    target_win = None
    for w in windows:
        if "thunar" in w.get("class", "").lower() or "thunar" in w.get("title", "").lower():
            target_win = w
            break
            
    if not target_win:
        return None
        
    win_class = target_win.get("class", "")
    
    # Check current view mode via AT-SPI
    desktop = Atspi.get_desktop(0)
    atspi_app = None
    for i in range(desktop.get_child_count()):
        child = desktop.get_child_at_index(i)
        if child:
            child_name = child.get_name() or ""
            if win_class.lower() in child_name.lower() or child_name.lower() in win_class.lower():
                atspi_app = child
                break
                
    if not atspi_app:
        return None
        
    view_mode = _get_thunar_view_mode(atspi_app)
    if not view_mode:
        return None
        
    if "details" in view_mode.lower():
        return None  # Already in Details view
        
    original_shortcut = None
    if "icon" in view_mode.lower():
        original_shortcut = "ctrl+1"
    elif "compact" in view_mode.lower():
        original_shortcut = "ctrl+3"
        
    if original_shortcut:
        # Switch to Details view (ctrl+2)
        focus_window(class_name=win_class)
        time.sleep(0.1)
        key("ctrl+2")
        time.sleep(0.2)  # Wait for tree to rebuild
        
    return original_shortcut


def _restore_thunar_view(app_class, original_shortcut):
    if not app_class or "thunar" not in app_class.lower() or not original_shortcut:
        return
    focus_window(class_name="thunar")
    time.sleep(0.1)
    key(original_shortcut)
    time.sleep(0.15)  # Wait for view to switch back


def click_element(app_class, element_name, button="left", click_count=1, role_hint=None):
    """Click a UI element by its accessible name. Resolution-independent.

    This searches the AT-SPI accessibility tree for an element matching
    `element_name` within the window matching `app_class`, then clicks
    its center using compositor-native pixel-perfect coordinates.

    Works regardless of window size, position, or screen resolution.
    Supports click_count (e.g. 2 for double click to open folders).
    """
    original_shortcut = _ensure_details_view(app_class)
    
    match = _find_atspi_element(app_class, element_name, role_hint)
    if not match:
        _restore_thunar_view(app_class, original_shortcut)
        return {"success": False, "error": f"Element '{element_name}' not found in '{app_class}'"}

    # Click at the element's absolute center
    # Compositor warp positions cursor on target surface, ydotool delivers click
    # No need to focus_window — cursor position determines click target on Wayland
    success = click(x=match["x"], y=match["y"], button=button, click_count=click_count)
    
    _restore_thunar_view(app_class, original_shortcut)
    
    return {
        "success": success,
        "element": match["name"],
        "role": match["role"],
        "clicked_at": {"x": match["x"], "y": match["y"]},
        "bounds": match["bounds"]
    }



def double_click(x=None, y=None, button="left", window_index=None, windows=None):
    """Double-click at exact pixel coordinates."""
    return click(x=x, y=y, button=button, click_count=2, window_index=window_index, windows=windows)


def double_click_element(app_class, element_name, role_hint=None):
    """Double-click a UI element by its accessible name.
    
    Excellent for opening folders/files in file managers like Thunar.
    """
    return click_element(app_class, element_name, button="left", click_count=2, role_hint=role_hint)


def list_elements(app_class):
    """List all accessible UI elements in a window. Useful for discovering element names."""
    original_shortcut = _ensure_details_view(app_class)
    
    try:
        import gi
        gi.require_version('Atspi', '2.0')
        from gi.repository import Atspi
    except Exception:
        _restore_thunar_view(app_class, original_shortcut)
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
        _restore_thunar_view(app_class, original_shortcut)
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
        _restore_thunar_view(app_class, original_shortcut)
        return {"success": False, "error": f"No AT-SPI app matches '{app_class}'"}

    elements = []

    def collect(node, depth=0):
        if depth > 20 or len(elements) >= 250:  # Increase depth to fully scan Thunar list view
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
    
    _restore_thunar_view(app_class, original_shortcut)
    
    return {"success": True, "app": win_class, "elements": elements, "count": len(elements)}


# ─── Keyboard Input ──────────────────────────────────────────────────────────

def type_text(text):
    """Type text at current cursor position."""
    result = subprocess.run(
        ["ydotool", "type", "--", text], capture_output=True, text=True
    )
    return result.returncode == 0


def key(keys):
    """Press key combination. Supports modifiers, e.g. 'alt+left', 'ctrl+shift+t', 'escape'"""
    # Scan code map
    scancodes = {
        "ctrl": 29, "leftctrl": 29, "rightctrl": 97,
        "alt": 56, "leftalt": 56, "rightalt": 100,
        "shift": 42, "leftshift": 42, "rightshift": 54,
        "super": 125, "meta": 125, "leftmeta": 125, "win": 125,
        "escape": 1, "esc": 1,
        "1": 2, "2": 3, "3": 4, "4": 5, "5": 6, "6": 7, "7": 8, "8": 9, "9": 10, "0": 11,
        "backspace": 14,
        "tab": 15,
        "q": 16, "w": 17, "e": 18, "r": 19, "t": 20, "y": 21, "u": 22, "i": 23, "o": 24, "p": 25,
        "enter": 28, "return": 28,
        "a": 30, "s": 31, "d": 32, "f": 33, "g": 34, "h": 35, "j": 36, "k": 37, "l": 38,
        "z": 44, "x": 45, "c": 46, "v": 47, "b": 48, "n": 49, "m": 50,
        "space": 57,
        "f1": 59, "f2": 60, "f3": 61, "f4": 62, "f5": 63, "f6": 64, "f7": 65, "f8": 66, "f9": 67, "f10": 68,
        "home": 102, "up": 103, "pageup": 104, "left": 105, "right": 106, "end": 107, "down": 108, "pagedown": 109,
        "insert": 110, "delete": 111,
        "f11": 87, "f12": 88
    }
    
    parts = [p.strip().lower() for p in keys.split("+") if p.strip()]
    if not parts:
        return False
        
    codes = []
    for p in parts:
        if p in scancodes:
            codes.append(scancodes[p])
        else:
            return False
            
    # Format ydotool key sequence:
    # Key downs: e.g. "29:1 56:1 105:1"
    # Key ups: e.g. "105:0 56:0 29:0" (in reverse order!)
    key_str_parts = []
    for c in codes:
        key_str_parts.append(f"{c}:1")
    for c in reversed(codes):
        key_str_parts.append(f"{c}:0")
        
    result = subprocess.run(
        ["ydotool", "key"] + key_str_parts,
        capture_output=True, text=True
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
        # Usage: click <x> <y> [button] [click_count]
        x, y = int(sys.argv[2]), int(sys.argv[3])
        button = "left"
        click_count = 1
        if len(sys.argv) > 4:
            if sys.argv[4].isdigit():
                click_count = int(sys.argv[4])
            else:
                button = sys.argv[4]
                if len(sys.argv) > 5 and sys.argv[5].isdigit():
                    click_count = int(sys.argv[5])
        success = click(x=x, y=y, button=button, click_count=click_count)
        print(json.dumps({"success": success, "x": x, "y": y, "button": button, "click_count": click_count}))

    elif action == "click_element":
        # Usage: click_element <app_class> <element_name> [button] [click_count]
        args = sys.argv[2:]
        if len(args) < 2:
            print(json.dumps({"error": "Usage: click_element <app_class> <element_name> [button] [click_count]"}))
            return
            
        app_class = args[0]
        remaining = args[1:]
        
        click_count = 1
        button = "left"
        
        # Check if the last argument is a click count (integer)
        if len(remaining) >= 2 and remaining[-1].isdigit():
            click_count = int(remaining[-1])
            remaining = remaining[:-1]
            
        # Check if the next last argument is a button name
        if len(remaining) >= 2 and remaining[-1].lower() in {"left", "right", "middle"}:
            button = remaining[-1].lower()
            remaining = remaining[:-1]
            
        element_name = " ".join(remaining)
        result = click_element(app_class, element_name, button=button, click_count=click_count)
        print(json.dumps(result, indent=2))

    elif action == "double_click":
        # Usage: double_click <x> <y> [button]
        x, y = int(sys.argv[2]), int(sys.argv[3])
        button = sys.argv[4] if len(sys.argv) > 4 else "left"
        success = double_click(x=x, y=y, button=button)
        print(json.dumps({"success": success, "x": x, "y": y, "button": button}))

    elif action == "double_click_element":
        # Usage: double_click_element <app_class> <element_name>
        args = sys.argv[2:]
        if len(args) < 2:
            print(json.dumps({"error": "Usage: double_click_element <app_class> <element_name>"}))
            return
            
        app_class = args[0]
        element_name = " ".join(args[1:])
        result = double_click_element(app_class, element_name)
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
