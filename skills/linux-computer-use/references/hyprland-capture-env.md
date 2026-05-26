# Hyprland capture env notes

When screen capture or cursor queries are run outside the compositor process context, Hyprland IPC may fail unless the live session signature is exported.

Observed working pattern on this machine:

```bash
export XDG_RUNTIME_DIR="/run/user/$UID"
export HYPRLAND_INSTANCE_SIGNATURE="$(ls -1 /run/user/$UID/hypr | tail -n 1)"
```

Then commands like these work from a shell:

```bash
hyprctl cursorpos
hyprctl clients -j
python3 ~/.hermes/skills/linux-computer-use/screen_control.py capture
```

Vision-tool note:
- pass screenshots as `file:///absolute/path/to/image.png` when using `vision_analyze`
- local bare paths may be rejected by the vision backend depending on transport

This note is about session-independent capture plumbing, not app-specific behavior.
