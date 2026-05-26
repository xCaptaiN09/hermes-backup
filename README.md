# Hermes Hyprland Setup

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform: Arch Linux](https://img.shields.io/badge/platform-Arch%20Linux-blue.svg)](https://archlinux.org/)
[![Engine: Hermes Agent](https://img.shields.io/badge/engine-Hermes%20Agent-purple.svg)](https://github.com/NousResearch/hermes-agent)
[![Setup: Compile--Free](https://img.shields.io/badge/setup-Compile--Free-success)](https://github.com/xCaptaiN09/hermes-hyprland-setup)

> [!WARNING]
> **Experimental & Under Active Development**
> This backup configuration, automation environment, and associated restoration files are under active, experimental development and are **not a final-grade production product**. System-level automation, file-system patching, and approval overrides can interact unpredictably with security policies, desktop configuration updates, and hardware drivers. Ensure you have proper system backups before attempting full restoration.

This repository stores all critical configurations, memories, patched files, and integration drivers to completely restore the **Hermes Agent** on a new Arch Linux + Hyprland installation.

With our pre-compiled C++ compositor plugin binary backed up directly in this folder, you **do not need to compile anything** or keep the development repository cloned. Setting up the agent on a new system is completely compile-free and takes seconds.

---

## What's in Here

*   `config.yaml` — Main Hermes config (active model configurations, auxiliary providers, system bounds).
*   `memories/` — Dynamic long-term files `MEMORY.md` and `USER.md` mapping the agent's memory.
*   `hermes-hyprland.so` — **[Pre-compiled Binary]** The compositor-level window mapping plugin.
*   `hyprland_backend.py` — The native Linux computer-use driver implementing Wayland cropped screenshotting (`grim`), SOM overlays (`Pillow`), and pointer/key injections (`ydotool`).
*   `tool.py.patch` — Staged patch to hook our new backend directly into `hermes-agent/tools/computer_use/tool.py`.
*   `approval-source.py` — Patched approval file allowing reboot, poweroff, and shutdown triggers.
*   `approval-sitepackages.py` — Patched approval file for the system Python site-packages layout.
*   `hermes-gateway.service` — Systemd service definition to run the Telegram gateway as a daemon on login.
*   `hyprland.conf.snippet` — Snippet to auto-start `ydotoold` and load the compositor plugin.

---

## Setup & Restore on a New Linux Distro

Follow these simple steps to restore this exact pixel-perfect environment:

### Step 1: Install System Dependencies
Install core runtime utilities needed for Wayland automation:
```bash
sudo pacman -S ydotool grim slurp
```

### Step 2: Set Up the Compositor Plugin Binary
No compiling needed! Just copy the pre-compiled compositor plugin binary directly to the standard hidden plugins path:
```bash
mkdir -p /home/captain/.config/hypr/plugins
cp hermes-hyprland.so /home/captain/.config/hypr/plugins/hermes-hyprland.so
```
*Add to `~/.config/hypr/hyprland.conf` to autostart at boot:*
```ini
exec-once = ydotoold
plugin = /home/captain/.config/hypr/plugins/hermes-hyprland.so
```

### Step 3: Install & Sync the Hermes Agent
1.  Run the standard Hermes Agent installer:
    ```bash
    curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
    ```
2.  Copy your personal configurations and memories:
    ```bash
    cp config.yaml ~/.hermes/config.yaml
    cp -r memories/ ~/.hermes/memories/
    ```

### Step 4: Apply the Coordinate Fusion Backend
Copy our custom high-performance driver directly into the agent directory:
```bash
cp hyprland_backend.py ~/.hermes/hermes-agent/tools/computer_use/hyprland_backend.py
```

Apply the patch to hook it into the agent's main entry point:
```bash
cd ~/.hermes/hermes-agent
patch -p1 < /path/to/hermes-hyprland-setup/tool.py.patch
```

### Step 5: Apply Approval Patches (Unblocking reboot/shutdown)
Overwrite the hardline block definitions:
1.  **Agent Source**:
    ```bash
    cp /path/to/hermes-hyprland-setup/approval-source.py ~/.hermes/hermes-agent/tools/approval.py
    ```
2.  **System Python Site-Packages**:
    Locate your active python package location:
    ```bash
    python3 -c "import tools.approval; import inspect; print(inspect.getfile(tools.approval))"
    ```
    Overwrite that file with `approval-sitepackages.py` and clear its `__pycache__` folder.

---

## Verifying the Restored Environment

To verify that the entire pipeline is working on your new system, set the active backend environment variable and execute a simulated capture:
```bash
export HERMES_COMPUTER_USE_BACKEND=hyprland
python3 -c "
from tools.computer_use.tool import handle_computer_use
import json
print(handle_computer_use({'action': 'capture', 'mode': 'som'}))
"
```
