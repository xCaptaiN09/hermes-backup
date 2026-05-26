---
name: linux-computer-use
description: Control the Linux desktop remotely using screen_control.py on Wayland/Hyprland. Works like macOS computer_use.
version: 3.0.0
author: captain
license: MIT
metadata:
  hermes:
    tags: [linux, wayland, hyprland, screenshot, mouse, keyboard, desktop, remote-control, computer-use]
    category: software-development
---

# Linux Computer Use (Wayland/Hyprland)

**CRITICAL**: ALL desktop control MUST go through `screen_control.py`. 
**NEVER write inline Python** for mouse/keyboard actions. NEVER use ydotool directly.
Script: `~/.hermes/skills/linux-computer-use/screen_control.py`

## Environment Setup (run once per session)

```bash
export XDG_RUNTIME_DIR="/run/user/$UID"
export HYPRLAND_INSTANCE_SIGNATURE="$(ls -1 /run/user/$UID/hypr | tail -n 1)"
```

## Clicking Buttons/Elements (PREFERRED METHOD)

Use `click_element` to interact with buttons, menus, and named UI controls.
In Thunar, prefer `double_click_element` for folders/files *only if the name is clearly visible in the main pane*.
If a folder name is ambiguous or not visible, use `Ctrl+L` and type the exact path instead of searching by name.

```bash
# Click a button or tab by name
python3 ~/.hermes/skills/linux-computer-use/screen_control.py click_element thunar Home
python3 ~/.hermes/skills/linux-computer-use/screen_control.py click_element thunar Desktop
python3 ~/.hermes/skills/linux-computer-use/screen_control.py click_element zen "New Tab"

# Double-click a folder or file to open it in Thunar when the item is clearly visible
python3 ~/.hermes/skills/linux-computer-use/screen_control.py double_click_element thunar LocalSend
python3 ~/.hermes/skills/linux-computer-use/screen_control.py double_click_element thunar "bootimg-tools"
```

If `double_click_element` resolves the wrong control in Thunar, fall back to `Ctrl+L` + exact path entry and verify the frame title after navigation.
## Discovering Available Elements

Before clicking, list what elements are available in an app:

```bash
python3 ~/.hermes/skills/linux-computer-use/screen_control.py list_elements thunar
python3 ~/.hermes/skills/linux-computer-use/screen_control.py list_elements zen
```

## Other Actions

### Capture Screen
```bash
python3 ~/.hermes/skills/linux-computer-use/screen_control.py capture
python3 ~/.hermes/skills/linux-computer-use/screen_control.py capture thunar
```

### Get Windows
```bash
python3 ~/.hermes/skills/linux-computer-use/screen_control.py windows
```

### Get Cursor Position
```bash
python3 ~/.hermes/skills/linux-computer-use/screen_control.py cursor
```

### Click at Exact Coordinates (only when click_element won't work)
```bash
# Single click at X Y coordinates
python3 ~/.hermes/skills/linux-computer-use/screen_control.py click 960 540
# Right click at coordinates
python3 ~/.hermes/skills/linux-computer-use/screen_control.py click 960 540 right
# Double click at coordinates
python3 ~/.hermes/skills/linux-computer-use/screen_control.py click 960 540 left 2
```

### Move Mouse
```bash
python3 ~/.hermes/skills/linux-computer-use/screen_control.py move 960 540
```

### Type Text
```bash
python3 ~/.hermes/skills/linux-computer-use/screen_control.py type "hello world"
```

### Key Shortcuts
```bash
# Supports full modifier chaining (ctrl, alt, shift, super/meta) and directional keys
python3 ~/.hermes/skills/linux-computer-use/screen_control.py key alt+left
python3 ~/.hermes/skills/linux-computer-use/screen_control.py key alt+right
python3 ~/.hermes/skills/linux-computer-use/screen_control.py key ctrl+shift+t
python3 ~/.hermes/skills/linux-computer-use/screen_control.py key return
python3 ~/.hermes/skills/linux-computer-use/screen_control.py key escape
python3 ~/.hermes/skills/linux-computer-use/screen_control.py key ctrl+c
python3 ~/.hermes/skills/linux-computer-use/screen_control.py key super
```

### Focus Window
```bash
python3 ~/.hermes/skills/linux-computer-use/screen_control.py focus thunar
```

## Standard Workflow

1. **Focus the app**: `focus <app_class>`
2. **Discover elements**: `list_elements <app_class>` to see available buttons/menus
3. **Click by name**: `click_element <app_class> <element_name>` (ALWAYS prefer this)
4. **Verify**: capture screen and check result
5. **Retry if needed**
6. **After directory navigation, re-run `list_elements` or capture** to confirm the current folder title and the visible items match the intended destination.
7. **Do not announce success from a click alone.** In Thunar, trust the window title/path change (`<folder> - Thunar`) as the confirmation signal; if the user says it did not open, capture again before replying.
8. **For file managers, prefer main-pane items or exact path entry** when accessible names are ambiguous; verify the folder title after every hop.
9. **Do not guess folder positions from screenshots** when Thunar has an accessible-path alternative. If the item name is visible but `click_element` misfires, use `Ctrl+L` and type the exact path.
10. **For image/file opening tests, verify the actual target content opened, not just the click success.**
11. **Do not rely on search results for folder-opening tests** if the goal is to validate direct navigation.
12. **If a direct double-click misresolves in Thunar, fall back to exact path entry first**; only use coordinate double-clicks if there is no reliable path-based route.
13. **Back navigation should be verified** after use. If `Alt+Left` does not change the title/path as expected, use the visible `Back` button instead.
14. **Thunar Search-Based Navigation Workflow**: If asked to open a folder/file via Thunar search, you MUST strictly follow this sequence:
    - **Focus Thunar**: `focus thunar`
    - **Open Search**: `click_element thunar "Search for Files..."`
    - **Type the query**: Wait 200ms, then use the `type` action to type the exact name (e.g. `type "LocalSend"`).
    - **Wait for results**: Wait 400ms for Thunar to populate search results.
    - **Open target**: Use `list_elements thunar` to locate the target item in the search results, and then `double_click_element thunar <foldername>` (or select it and send `key return`) to open it.
    - **Verify open state**: Run `list_elements thunar` or `capture thunar` and check that the window title/frame matches the target name (e.g., `LocalSend - Thunar`). **NEVER announce that a folder was successfully opened unless you have explicitly verified that the window title changed to that folder name!**

See `references/thunar-navigation-notes.md` for Thunar-specific failure modes and recovery patterns.

## IMPORTANT RULES

1. **ALWAYS use click_element for buttons, menus, and named UI elements** — it finds the element regardless of window size/position
2. **NEVER write inline Python scripts** for mouse/keyboard — ALWAYS call screen_control.py
3. **NEVER use ydotool directly** — screen_control.py handles input via compositor socket
4. Only use coordinate `click X Y` as a last resort when the element has no accessible name
5. Use `list_elements` first if you're unsure what the element is called
6. If the requested folder/item name is not visible, verify the current directory title and visible entries before assuming the target exists; use search only after that check.
7. In Thunar specifically, `click_element` can resolve to the search toggle or status row instead of the folder item. If that happens, use `Ctrl+L` and type the exact path rather than hunting by name.
8. Do not trust a click result alone for file operations; confirm by title change or refreshed `list_elements`.
9. For images, the browser/file-URI path may be enough for verification, but native desktop-launch support still needs explicit coverage if that is part of the test.
10. `double_click_element` is expected to be available in the script; if it is missing, update `screen_control.py` first rather than documenting unsupported usage.
11. **NEVER announce success from a search click alone**. Clicking search merely activates the input box. You must type the target name, wait for the result list to render, double-click/open the result, and verify that the window title/path changed to the target folder before replying.


## Requirements


## Requirements
- grimblast (AUR) - screenshot with cursor visible
- hyprctl - window positions
- hermes-hyprland plugin loaded (provides /tmp/hermes-hyprland.sock)
- AT-SPI enabled (for click_element — most GTK/Qt apps support this)
- cursor:no_hardware_cursors = true in hyprland.conf
