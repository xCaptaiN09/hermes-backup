---
name: linux-computer-use
description: Control the Linux desktop remotely using screen_control.py on Wayland/Hyprland. Works like macOS computer_use.
version: 2.0.0
author: captain
license: MIT
metadata:
  hermes:
    tags: [linux, wayland, hyprland, screenshot, mouse, keyboard, desktop, remote-control, ydotool, grimblast, computer-use]
    category: software-development
---

# Linux Computer Use (Wayland/Hyprland)

Use screen_control.py for all desktop control.
Script: ~/.hermes/skills/linux-computer-use/screen_control.py

Works like macOS computer_use - capture screen, get window positions, click by coordinates.

## Always Start With Capture

terminal("python3 ~/.hermes/skills/linux-computer-use/screen_control.py capture")

Returns screenshot path, cursor position, all windows with exact positions.

## Actions

### Capture (with optional app filter)
terminal("python3 ~/.hermes/skills/linux-computer-use/screen_control.py capture")
terminal("python3 ~/.hermes/skills/linux-computer-use/screen_control.py capture firefox")

### Get Windows
terminal("python3 ~/.hermes/skills/linux-computer-use/screen_control.py windows")

### Get Cursor Position
terminal("python3 ~/.hermes/skills/linux-computer-use/screen_control.py cursor")

### Move Mouse
terminal("python3 ~/.hermes/skills/linux-computer-use/screen_control.py move 960 540")

### Click
terminal("python3 ~/.hermes/skills/linux-computer-use/screen_control.py click 960 540")
terminal("python3 ~/.hermes/skills/linux-computer-use/screen_control.py click 960 540 right")

### Type Text
terminal("python3 ~/.hermes/skills/linux-computer-use/screen_control.py type hello world")

### Key Shortcuts
terminal("python3 ~/.hermes/skills/linux-computer-use/screen_control.py key return")
terminal("python3 ~/.hermes/skills/linux-computer-use/screen_control.py key escape")
terminal("python3 ~/.hermes/skills/linux-computer-use/screen_control.py key ctrl+c")
terminal("python3 ~/.hermes/skills/linux-computer-use/screen_control.py key ctrl+v")
terminal("python3 ~/.hermes/skills/linux-computer-use/screen_control.py key ctrl+s")
terminal("python3 ~/.hermes/skills/linux-computer-use/screen_control.py key super")

### Focus Window
terminal("python3 ~/.hermes/skills/linux-computer-use/screen_control.py focus firefox")

## Standard Workflow

1. Capture screen - get windows + screenshot
2. Send screenshot to vision with window boundaries for accurate coordinate detection
3. Vision returns x,y of target element
4. Click at coordinates
5. Verify - capture again, check cursor position, check UI changed
6. Retry if needed

## Vision Prompt Template

When asking vision for coordinates, include window boundaries:
This is a 1920x1080 screenshot. The target window TITLE is at x=X, y=Y, width=W, height=H.
Find ELEMENT within this window and return ONLY JSON: {x: N, y: N}

## Verification After Every Click

terminal("python3 ~/.hermes/skills/linux-computer-use/screen_control.py cursor")
terminal("python3 ~/.hermes/skills/linux-computer-use/screen_control.py capture")

## Send Screenshot to Telegram

terminal("python3 ~/.hermes/skills/linux-computer-use/screen_control.py capture")
Then send /tmp/hermes_screen.png via messaging tool.

## Requirements
- grimblast (AUR) - screenshot with cursor visible
- ydotool + ydotoold running
- hyprctl - window positions
- cursor:no_hardware_cursors = true in hyprland.conf
