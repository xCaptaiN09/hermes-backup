---
name: linux-computer-use
description: "Control the Linux desktop remotely: screenshots, mouse, click, type using grim and ydotool on Wayland/Hyprland."
version: 1.0.0
author: captain
license: MIT
metadata:
  hermes:
    tags: [linux, wayland, hyprland, screenshot, mouse, keyboard, desktop, remote-control, ydotool, grim]
    category: software-development
---

# Linux Computer Use (Wayland/Hyprland)

Control Arch Linux Hyprland desktop using grim for screenshots and ydotool for mouse/keyboard input. Resolution: 1920x1080.

## Check ydotoold Running
Always check first:
terminal('pgrep ydotoold || (ydotoold & sleep 1)')

If ydotool socket connection fails, use the fallback notes in `references/wayland-input-fallbacks.md`.

## Screenshot
terminal('grim /tmp/hermes_screen.png')

## Analyze Screenshot for Coordinates
Take screenshot, then ask vision: "Return ONLY JSON with x,y of [element]: {x: 100, y: 200}"
Use returned coordinates for mouse operations.

## Mouse Move
terminal('ydotool mousemove --absolute -x X -y Y')

## Click
terminal('ydotool click 0xC0')

## Right Click
terminal('ydotool click 0xC8')

## Double Click
terminal('ydotool click 0xC0 && sleep 0.1 && ydotool click 0xC0')

## Type Text
terminal('ydotool type "text here"')

## Key Shortcuts
terminal('ydotool key 28:1 28:0')   # Enter
terminal('ydotool key 1:1 1:0')    # Escape
terminal('ydotool key 29:1 46:1 46:0 29:0')  # Ctrl+C

## Full Remote Control Flow
1. pgrep ydotoold or start it
2. grim /tmp/hermes_screen.png
3. vision_analyze — get x,y of target
4. ydotool mousemove to x,y
5. ydotool click 0xC0
6. grim /tmp/hermes_screen2.png — verify
7. send screenshot to Telegram

## Send Screenshot to Telegram
terminal('grim /tmp/hermes_screen.png')
messaging_send(image='/tmp/hermes_screen.png')
