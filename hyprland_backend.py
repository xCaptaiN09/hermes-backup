"""Linux Wayland / Hyprland Coordinate Fusion Backend.

Exposes pixel-perfect desktop automation under Wayland by fusing compositor geometries
with system AT-SPI D-Bus accessibility hierarchies. Uses `grim` for screenshotting
and `ydotool` for mouse and keyboard event simulation.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from tools.computer_use.backend import (
    ActionResult,
    CaptureResult,
    ComputerUseBackend,
    UIElement as AgentUIElement,
)

# Append C++ plugin workspace to sys.path to import our fusion client
sys.path.append("/home/captain/Antigravity/hermes_hyprland_plugin/hermes-hyprland-plugin")
try:
    from hermes_hyprland_fusion import CoordinateFusionEngine, ATSPI_AVAILABLE
except ImportError:
    ATSPI_AVAILABLE = False
    CoordinateFusionEngine = None

logger = logging.getLogger(__name__)


class HyprlandBackend(ComputerUseBackend):
    """Hermes Agent Computer Use Backend for Linux/Hyprland."""

    def __init__(self) -> None:
        self.engine = None
        self._active_window_class: Optional[str] = None
        self._active_window_address: Optional[str] = None
        self._active_window_title: Optional[str] = None
        self._active_geometry: Tuple[int, int, int, int] = (0, 0, 0, 0)
        self._last_app: Optional[str] = None
        # Store last mapped elements for click-by-index resolution
        self._cached_elements: List[Any] = []

    # ── Lifecycle ──────────────────────────────────────────────────
    def start(self) -> None:
        if CoordinateFusionEngine is None:
            raise RuntimeError("CoordinateFusionEngine could not be imported from the plugin directory.")
        self.engine = CoordinateFusionEngine()
        logger.info("Hyprland Coordinate Fusion Backend started successfully.")

    def stop(self) -> None:
        logger.info("Hyprland Coordinate Fusion Backend stopped.")

    def is_available(self) -> bool:
        # Verified under Linux with Hyprland C++ plugin sock alive
        is_linux = sys.platform == "linux"
        sock_exists = os.path.exists("/tmp/hermes-hyprland.sock")
        return is_linux and sock_exists and ATSPI_AVAILABLE

    # ── Capture ────────────────────────────────────────────────────
    def capture(self, mode: str = "som", app: Optional[str] = None) -> CaptureResult:
        """Captures the active on-screen window (optionally filtered by class).

        Fuses active compositor frames with D-Bus AT-SPI accessibility trees.
        """
        # Step 1: Query all mapped windows
        windows = self.engine.get_windows()
        if not windows:
            return CaptureResult(mode=mode, width=0, height=0, png_b64=None,
                                 elements=[], app="", window_title="", png_bytes_len=0)

        # Step 2: Determine target window
        target_win = None
        if app:
            app_lower = app.lower()
            for w in windows:
                if app_lower in w.get("class", "").lower() or app_lower in w.get("title", "").lower():
                    target_win = w
                    break
            if not target_win:
                logger.warning("No window matched app: %s", app)
                return CaptureResult(
                    mode=mode, width=0, height=0, png_b64=None, elements=[],
                    app="", window_title=f"<no window matched app: {app}>", png_bytes_len=0
                )
        else:
            # Fall back to focused window
            for w in windows:
                if w.get("focused"):
                    target_win = w
                    break
            if not target_win:
                target_win = windows[0]  # Grab first available window

        # Cache geometry and class details
        win_x = target_win["x"]
        win_y = target_win["y"]
        win_w = target_win["width"]
        win_h = target_win["height"]
        self._active_geometry = (win_x, win_y, win_w, win_h)
        self._active_window_class = target_win["class"]
        self._active_window_address = target_win["address"]
        self._active_window_title = target_win["title"]
        self._last_app = target_win["class"]

        png_b64: Optional[str] = None
        agent_elements: List[AgentUIElement] = []

        # Step 3: Screenshot Crop via native Wayland 'grim'
        screenshot_path = "/tmp/hermes_capture.png"
        if mode in {"som", "vision"}:
            try:
                # Remove stale screenshot
                if os.path.exists(screenshot_path):
                    os.unlink(screenshot_path)
                
                # Capture only the target window area using grim -g
                geom_str = f"{win_x},{win_y} {win_w}x{win_h}"
                subprocess.run(
                    ["/usr/bin/grim", "-g", geom_str, screenshot_path],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except Exception as e:
                logger.error("grim screenshot capture failed: %s", e)

        # Step 4: Perform Coordinate Fusion Traversal
        if mode in {"som", "ax"}:
            try:
                fused_elements = self.engine.get_clickable_elements(self._active_window_class)
                self._cached_elements = fused_elements
                
                # Map fused elements to agent-expected UIElement instances
                for el in fused_elements:
                    agent_elements.append(
                        AgentUIElement(
                            index=el.index,
                            role=el.role,
                            label=el.label,
                            bounds=el.bounds,
                            app=el.app,
                            pid=0,
                            window_id=int(el.window_id) if el.window_id.isdigit() else 0
                        )
                    )
            except Exception as e:
                logger.error("AT-SPI element coordinate fusion failed: %s", e)

        # Step 5: Draw visual SOM index bubbles over the screenshot locally via Pillow
        if mode == "som" and os.path.exists(screenshot_path) and agent_elements:
            try:
                from PIL import Image, ImageDraw
                img = Image.open(screenshot_path)
                draw = ImageDraw.Draw(img)

                # Surfacing index indicators over target clickable boundaries
                for el in agent_elements[:200]:  # Cap to avoid overlay overcrowding
                    ex, ey, ew, eh = el.bounds
                    
                    # Convert absolute screen bounds to window-cropped image offset
                    rx = ex - win_x
                    ry = ey - win_y
                    
                    # Draw a nice dark-red rounded label bubble with white text
                    # Clamped bounding offsets
                    rx = max(2, min(rx, win_w - 30))
                    ry = max(2, min(ry, win_h - 20))
                    
                    draw.rounded_rectangle(
                        [rx, ry, rx + 24, ry + 16],
                        radius=3,
                        fill=(220, 53, 69, 230),      # Bootstrap danger color red, alpha transparent
                        outline=(255, 255, 255, 255),
                        width=1
                    )
                    # Use default bitmap text overlay
                    draw.text((rx + 4, ry + 2), str(el.index), fill="white")
                
                img.save(screenshot_path, "PNG")
            except Exception as e:
                logger.error("Pillow SOM rendering failed: %s", e)

        # Encode screenshot to base64
        if os.path.exists(screenshot_path) and mode in {"som", "vision"}:
            try:
                with open(screenshot_path, "rb") as f:
                    png_b64 = base64.b64encode(f.read()).decode("utf-8")
            except Exception as e:
                logger.error("Failed to read encoded screenshot: %s", e)
            finally:
                # Clean up temporary capture
                if os.path.exists(screenshot_path):
                    try:
                        os.unlink(screenshot_path)
                    except Exception:
                        pass

        png_len = len(png_b64) * 3 // 4 if png_b64 else 0
        return CaptureResult(
            mode=mode,
            width=win_w,
            height=win_h,
            png_b64=png_b64,
            elements=agent_elements,
            app=self._active_window_class or "",
            window_title=self._active_window_title or "",
            png_bytes_len=png_len
        )

    # ── Pointer Actions ────────────────────────────────────────────
    def click(
        self,
        *,
        element: Optional[int] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
        click_count: int = 1,
        modifiers: Optional[List[str]] = None,
    ) -> ActionResult:
        # Resolve target click coordinate
        target_x, target_y = None, None

        if element is not None:
            # Match element index in cached tree
            matched = next((e for e in self._cached_elements if e.index == element), None)
            if matched:
                target_x, target_y = matched.center()
                logger.info("Resolved element #%d target coordinate to X=%d, Y=%d", element, target_x, target_y)
            else:
                return ActionResult(ok=False, action="click", message=f"Could not find cached element #{element}")
        elif x is not None and y is not None:
            target_x, target_y = x, y
        else:
            return ActionResult(ok=False, action="click", message="Click action requires element or coordinate arguments.")

        success = self.engine.click_xy(target_x, target_y, button=button, count=click_count)
        msg = f"Clicked button={button} at X={target_x}, Y={target_y} successfully." if success else "Input click dispatch failed."
        return ActionResult(ok=success, action="click", message=msg)

    def drag(
        self,
        *,
        from_element: Optional[int] = None,
        to_element: Optional[int] = None,
        from_xy: Optional[Tuple[int, int]] = None,
        to_xy: Optional[Tuple[int, int]] = None,
        button: str = "left",
        modifiers: Optional[List[str]] = None,
    ) -> ActionResult:
        fx, fy = None, None
        tx, ty = None, None

        # Resolve source target
        if from_element is not None:
            matched = next((e for e in self._cached_elements if e.index == from_element), None)
            if matched:
                fx, fy = matched.center()
        elif from_xy is not None:
            fx, fy = from_xy

        # Resolve destination target
        if to_element is not None:
            matched = next((e for e in self._cached_elements if e.index == to_element), None)
            if matched:
                tx, ty = matched.center()
        elif to_xy is not None:
            tx, ty = to_xy

        if None in (fx, fy, tx, ty):
            return ActionResult(ok=False, action="drag", message="Invalid source or destination coordinate boundaries.")

        # Drag simulation via kernel-level pointer events
        try:
            # 1. Warp cursor to source coordinates
            self.engine.warp_cursor(fx, fy)
            time.sleep(0.1)
            
            # 2. Hold left mouse button down (BTN_LEFT keycode is 272)
            subprocess.run(["ydotool", "key", "272:1"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.1)
            
            # 3. Warp cursor to destination coordinates
            self.engine.warp_cursor(tx, ty)
            time.sleep(0.1)
            
            # 4. Release left mouse button (BTN_LEFT keycode is 272)
            subprocess.run(["ydotool", "key", "272:0"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.1)
            
            return ActionResult(ok=True, action="drag", message=f"Dragged from ({fx},{fy}) to ({tx},{ty}).")
        except Exception as e:
            # Ensure safety release of left button in case of failure
            try:
                subprocess.run(["ydotool", "key", "272:0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            return ActionResult(ok=False, action="drag", message=f"Drag dispatch failure: {str(e)}")

    def scroll(
        self,
        *,
        direction: str,
        amount: int = 3,
        element: Optional[int] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
        modifiers: Optional[List[str]] = None,
    ) -> ActionResult:
        # Resolve center or cursor position
        tx, ty = None, None
        if element is not None:
            matched = next((e for e in self._cached_elements if e.index == element), None)
            if matched:
                tx, ty = matched.center()
        elif x is not None and y is not None:
            tx, ty = x, y

        if tx is not None and ty is not None:
            self.engine.warp_cursor(tx, ty)

        # Map direction to wheel movements via ydotool
        # ydotool uses keycodes or direct mouse scroll motions:
        # ydotool commands: 'mousemove' or click modifiers. 
        # For simplicity, dispatch Hyprland scroll binds or ydotool triggers
        try:
            # standard wheel is simulated via mouse event injection:
            # scroll down is simulated via key wheel down:
            val = "-1" if direction == "down" else "1"
            # Execute ydotool wheel simulation
            for _ in range(amount):
                # Note: ydotool click 0xC4 simulates mouse wheel down, 0xC3 simulates mouse wheel up
                w_code = "0xC4" if direction == "down" else "0xC3"
                if direction == "left":
                    w_code = "0xC5"
                elif direction == "right":
                    w_code = "0xC6"
                subprocess.run(["ydotool", "click", w_code], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return ActionResult(ok=True, action="scroll", message=f"Scrolled {direction} x{amount}.")
        except Exception as e:
            return ActionResult(ok=False, action="scroll", message=f"Scroll failure: {e}")

    # ── Keyboard Actions ───────────────────────────────────────────
    def type_text(self, text: str) -> ActionResult:
        try:
            # Inject keyboard typing via native ydotool type engine
            subprocess.run(["ydotool", "type", text], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return ActionResult(ok=True, action="type_text", message=f"Typed text: {text}")
        except Exception as e:
            return ActionResult(ok=False, action="type_text", message=f"Keyboard type failure: {e}")

    def key(self, keys: str) -> ActionResult:
        try:
            # Map key triggers (combos like cmd+s, ctrl+alt+t)
            # ydotool key keycodes: e.g. ctrl+alt+t
            # Map common keyboard keys to ydotool commands:
            parts = [p.strip().lower() for p in keys.split("+") if p.strip()]
            
            # ydotool key combo execution:
            # ydotool key modifier:down key:down key:up modifier:up
            # Simple wrapper for single keys (e.g. "Return", "BackSpace")
            key_map = {
                "return": "28", "enter": "28",
                "backspace": "14", "tab": "15",
                "space": "57", "escape": "1",
                "up": "103", "down": "108", "left": "105", "right": "106",
                "a": "30", "c": "46", "v": "47", "s": "31"
            }
            
            # For standard commands, execute directly:
            # We can use 'wtype' if ydotool is too strict, or standard ydotool keycodes
            # Let's map standard keystrokes or fall back to wtype if present
            # As a universally robust backup, standard key simulation is clean:
            codes = []
            for p in parts:
                code = key_map.get(p)
                if code:
                    codes.append(code)
            
            if codes:
                # Key down
                for c in codes:
                    subprocess.run(["ydotool", "key", f"{c}:1"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                # Key up
                for c in reversed(codes):
                    subprocess.run(["ydotool", "key", f"{c}:0"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return ActionResult(ok=True, action="key", message=f"Executed hotkey combo: {keys}")
            
            # Default to wtype or quick key injection
            subprocess.run(["ydotool", "type", keys], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return ActionResult(ok=True, action="key", message=f"Injected text keys: {keys}")
        except Exception as e:
            return ActionResult(ok=False, action="key", message=f"Keystroke hotkey failure: {e}")

    # ── Introspection & Mutators ───────────────────────────────────
    def list_apps(self) -> List[Dict[str, Any]]:
        # Enumerate running compositor window classes
        windows = self.engine.get_windows()
        apps = []
        for w in windows:
            apps.append({
                "name": w["class"],
                "pid": 0,
                "window_count": 1,
                "title": w["title"]
            })
        return apps

    def focus_app(self, app: str, raise_window: bool = False) -> ActionResult:
        res = self.engine.client.send_command({"action": "focus_window", "class": app})
        if res.get("success"):
            self._last_app = app
            return ActionResult(ok=True, action="focus_app", message=f"Focused application {app} successfully.")
        return ActionResult(ok=False, action="focus_app", message=f"Failed to focus window: {res.get('error')}")

    def set_value(self, value: str, element: Optional[int] = None) -> ActionResult:
        # Focus text widget, select all, and type value
        if element is not None:
            click_res = self.click(element=element)
            if not click_res.ok:
                return click_res
        
        # Select all and type
        self.key("ctrl+a")
        time.sleep(0.1)
        self.key("backspace")
        time.sleep(0.1)
        return self.type_text(value)
