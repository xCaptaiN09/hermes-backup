# Hermes Agent Backup

Setup backup for Hermes Agent on Arch Linux + Hyprland.

## What's in here

- `config.yaml` — main Hermes config (model, gateway, memory, auxiliary providers)
- `memories/` — MEMORY.md and USER.md (agent memory about Cap)
- `skills/linux-computer-use/` — custom skill for desktop control via ydotool+grim
- `approval-source.py` — patched approval.py (reboot/shutdown unblocked)
- `approval-sitepackages.py` — patched approval.py for system Python site-packages

## Setup Summary

### Model
- Main: gpt-5.4-mini via GitHub Copilot (Student plan)
- Vision auxiliary: gpt-4.1 via GitHub Copilot (0x, unlimited)
- Other auxiliary: auto

### Telegram
- Bot configured with Cap's Telegram user ID as allowlist and home channel
- Gateway runs as systemd user service (auto-starts on login)

### Desktop Control
- grim — screenshots (Wayland)
- ydotool — mouse/keyboard control
- ydotoold auto-starts via hyprland.conf exec-once

### What was patched
Reboot/shutdown commands are hardline blocked by default in Hermes.
Two files needed patching to unblock them:
- `~/.hermes/hermes-agent/tools/approval.py`
- `~/.local/lib/python3.14/site-packages/tools/approval.py`

Lines commented out in HARDLINE_PATTERNS:
- `(_CMDPOS + r'(shutdown|reboot|halt|poweroff)\b', ...)`
- `(_CMDPOS + r'init\s+[06]\b', ...)`
- `(_CMDPOS + r'systemctl\s+(poweroff|reboot|halt|kexec)\b', ...)`
- `(_CMDPOS + r'telinit\s+[06]\b', ...)`

## Restore on New System

1. Install Hermes: `curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash`
2. Copy config: `cp config.yaml ~/.hermes/config.yaml`
3. Copy env: `cp .env ~/.hermes/.env`
4. Copy memories: `cp -r memories/ ~/.hermes/memories/`
5. Copy skill: `cp -r skills/ ~/.hermes/skills/`
6. Apply approval patch: `cp approval-source.py ~/.hermes/hermes-agent/tools/approval.py`
7. Find site-packages path: `/usr/bin/python -c "import tools.approval; import inspect; print(inspect.getfile(tools.approval))"`
8. Copy to that path and delete pyc cache
9. Install ydotool: `sudo pacman -S ydotool`
10. Add to hyprland: `echo "exec-once = ydotoold" >> ~/.config/hypr/hyprland.conf`
11. Run: `hermes gateway restart`

## Notes
- Tirith security is re-enabled (tirith_enabled: true)
- Approvals mode: manual (LLM decides, not hard block)
- Only disk destruction commands remain hardline blocked
- Gemini OAuth shared quota — don't set auxiliary providers to google-gemini-cli
