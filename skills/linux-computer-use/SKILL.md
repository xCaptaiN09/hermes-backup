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

Use `click_element` to click any button, menu, or UI element BY NAME.
This is resolution-independent and works regardless of window size or position.

```bash
# Click element by name — ALWAYS prefer this over coordinate clicking
python3 ~/.hermes/skills/linux-computer-use/screen_control.py click_element thunar Home
python3 ~/.hermes/skills/linux-computer-use/screen_control.py click_element thunar Desktop
python3 ~/.hermes/skills/linux-computer-use/screen_control.py click_element thunar Documents
python3 ~/.hermes/skills/linux-computer-use/screen_control.py click_element zen "New Tab"
python3 ~/.hermes/skills/linux-computer-use/screen_control.py click_element zen Back
```

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
python3 ~/.hermes/skills/linux-computer-use/screen_control.py click 960 540
python3 ~/.hermes/skills/linux-computer-use/screen_control.py click 960 540 right
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
python3 ~/.hermes/skills/linux-computer-use/screen_control.py key return
python3 ~/.hermes/skills/linux-computer-use/screen_control.py key escape
python3 ~/.hermes/skills/linux-computer-use/screen_control.py key ctrl+c
python3 ~/.hermes/skills/linux-computer-use/screen_control.py key ctrl+v
python3 ~/.hermes/skills/linux-computer-use/screen_control.py key ctrl+s
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

## IMPORTANT RULES

1. **ALWAYS use click_element for buttons, menus, and named UI elements** — it finds the element regardless of window size/position
2. **NEVER write inline Python scripts** for mouse/keyboard — ALWAYS call screen_control.py
3. **NEVER use ydotool directly** — screen_control.py handles input via compositor socket
4. Only use coordinate `click X Y` as a last resort when the element has no accessible name
5. Use `list_elements` first if you're unsure what the element is called

## Requirements
- grimblast (AUR) - screenshot with cursor visible
- hyprctl - window positions
- hermes-hyprland plugin loaded (provides /tmp/hermes-hyprland.sock)
- AT-SPI enabled (for click_element — most GTK/Qt apps support this)
- cursor:no_hardware_cursors = true in hyprland.conf
