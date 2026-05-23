# Wayland Input Fallbacks

Session note: `ydotool` can fail with `failed to connect socket /run/user/1000/.ydotool_socket: Connection refused` when `ydotoold` is not running or not accepting connections.

Practical fallback used on Hyprland:
- `hyprctl dispatch movecursor X Y` to move the cursor without relying on `ydotoold`
- `grim /tmp/hermes_screen.png` to capture the screen afterward

Use this as the first fallback when the ydotool daemon path is unavailable. Keep it out of the main skill body unless the fallback proves generally useful again.