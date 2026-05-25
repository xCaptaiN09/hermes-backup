# Hermes Agent Backup

This repository stores all critical configurations, memories, patched files, and integration drivers to completely restore the **Hermes Agent** on a new Arch Linux + Hyprland installation.

---

## What's in Here

*   `config.yaml` — Main Hermes config (active model configurations, auxiliary providers, system bounds).
*   `memories/` — Dynamic long-term files `MEMORY.md` and `USER.md` mapping the agent's memory.
*   `hyprland_backend.py` — **[v2.0 Upgrade]** The native Linux computer-use driver implementing Wayland cropped screenshotting (`grim`), SOM overlays (`Pillow`), and pointer/key injections (`ydotool`).
*   `tool.py.patch` — **[v2.0 Upgrade]** Staged patch to hook our new backend directly into `hermes-agent/tools/computer_use/tool.py`.
*   `approval-source.py` — Patched approval file allowing reboot, poweroff, and shutdown triggers.
*   `approval-sitepackages.py` — Patched approval file for the system Python site-packages layout.
*   `hermes-gateway.service` — Systemd service definition to run the Telegram gateway as a daemon on login.
*   `hyprland.conf.snippet` — Snippet to auto-start `ydotoold` and load the compositor plugin.

---

## Setup & Restore on a New Linux Distro

Follow these simple steps to restore this exact pixel-perfect environment:

### Step 1: Install System Dependencies
Install core packages needed for Wayland automation:
```bash
sudo pacman -S ydotool grim slurp cmake nlohmann-json libdrm pixman
```

### Step 2: Set Up the C++ Compositor Plugin
Clone, compile, and load the compositor IPC socket plugin:
```bash
git clone https://github.com/xCaptaiN09/hermes-hyprland-plugin.git
cd hermes-hyprland-plugin
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
hyprctl plugin load ./build/hermes-hyprland.so
```
*Add to `~/.config/hypr/hyprland.conf` to autostart at boot:*
```ini
exec-once = ydotoold
plugin = /absolute/path/to/hermes-hyprland-plugin/build/hermes-hyprland.so
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
patch -p1 < /path/to/hermes-backup/tool.py.patch
```

### Step 5: Apply Approval Patches (Unblocking reboot/shutdown)
Overwrite the hardline block definitions:
1.  **Agent Source**:
    ```bash
    cp /path/to/hermes-backup/approval-source.py ~/.hermes/hermes-agent/tools/approval.py
    ```
2.  **System Python Site-Packages**:
    Locate your active python package location:
    ```bash
    python3 -c "import tools.approval; import inspect; print(inspect.getfile(tools.approval))"
    ```
    Overwrite that file with `approval-sitepackages.py` and clear its `__pycache__` folder.

---

## Verifying the Restored Environment

To verify that the entire pipeline is working on your new system, set the active backend environment variable and execute the test runner:
```bash
export HERMES_COMPUTER_USE_BACKEND=hyprland
cd hermes-hyprland-plugin
./test_integration.sh
```
*If all checks report `SUCCESS`, your agent is ready to operate with pixel-perfect precision on Wayland!*
