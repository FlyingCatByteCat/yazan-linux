"""Core configuration, styling constants and shared helpers for the
Yazan Linux guided installer.

Styling is enforced here so that every screen and every console line uses
the exact same palette. No GUI, no GTK, no Qt -- pure terminal.
"""

import json
import os
import sys
from dataclasses import dataclass, field

OS_NAME = "Yazan Linux"
TAGLINE = "The Arch way, your way."
VERSION = "1.0.0"
LIVE_URL = "https://yazanlinux.org"

# --- Styling constants -------------------------------------------------------
# Accent color: Arch blue #1793D1 -> ANSI 24-bit true colour escape.
BLUE = "\033[38;2;23;147;209m"
GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[0;33m"
WHITE = "\033[0;37m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

OK = f"{GREEN}[OK]{RESET}"
BAR = f"{BLUE}[*]{RESET}"
ERROR = f"{RED}[ERROR]{RESET}"
WARN = f"{YELLOW}[WARN]{RESET}"

LOG_FILE = "/tmp/yazan-install.log"

# --- Asset helpers -----------------------------------------------------------
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(_BASE, "assets")
CONFIGS_DIR = os.path.join(_BASE, "configs")


def read_asset(name):
    path = os.path.join(ASSETS_DIR, name)
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read().rstrip("\n")


def tux():
    return read_asset("tux.txt")


def banner():
    return read_asset("banner.txt")


def log(msg, prefix=BAR):
    sys.stdout.write(f"{prefix} {msg}\n")
    sys.stdout.flush()


def log_ok(msg):
    log(msg, prefix=OK)


def log_warn(msg):
    log(msg, prefix=WARN)


def log_error(msg):
    log(msg, prefix=ERROR)


def load_component(cid):
    """Load a desktop component definition from configs/<id>.json."""
    path = os.path.join(CONFIGS_DIR, f"{cid}.json")
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    data.setdefault("services", [])
    return data


def list_components():
    """Return the available desktop component ids in a stable order."""
    order = ["kde", "gnome", "xfce", "hyprland", "i3", "sway", "openbox", "none"]
    present = []
    for cid in order:
        if os.path.exists(os.path.join(CONFIGS_DIR, f"{cid}.json")):
            present.append(cid)
    missing = sorted(
        f[:-5] for f in os.listdir(CONFIGS_DIR)
        if f.endswith(".json") and f[:-5] not in present
    )
    return present + missing


# --- Boot flow control --------------------------------------------------------
BOOT_CONTINUE = "boot"
BOOT_SHELL = "shell"


# --- Configuration object ------------------------------------------------------
@dataclass
class InstallConfig:
    """Everything the guided installer collects, carried between screens."""

    locale: str = "en_US.UTF-8"
    region: str = "America"
    city: str = "New_York"
    disk: str = ""
    disk_size: str = ""
    partition_mode: str = "auto"      # "auto" | "manual"
    filesystem: str = "btrfs"         # "ext4" | "btrfs" | "xfs"
    desktop_id: str = "none"
    bootloader: str = "grub"          # "grub" | "systemd-boot" | "refind"
    display_server: str = "wayland"   # "xorg" | "wayland"
    audio: str = "pipewire"           # "pipewire" | "pulseaudio"
    network: str = "NetworkManager"   # "NetworkManager" | "iwd" | "none"
    shell: str = "bash"               # "bash" | "zsh" | "fish"
    aur_helper: str = "none"          # "none" | "yay" | "paru"
    hostname: str = "yazanbox"
    username: str = ""
    user_password: str = ""
    root_password: str = ""
    manual_root: str = ""
    manual_boot: str = ""
    efi: bool = False

    def volume_partitions(self):
        """Return the partition node name for a given index (0-based)."""
        return self.disk

    def component(self):
        return load_component(self.desktop_id)

    def save(self, path="/tmp/yazan-config.json"):
        payload = {f: getattr(self, f) for f in self.__dataclass_fields__}
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)

    @classmethod
    def load(cls, path="/tmp/yazan-config.json"):
        cfg = cls()
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            for key, value in data.items():
                if hasattr(cfg, key):
                    setattr(cfg, key, value)
        except (OSError, json.JSONDecodeError):
            pass
        return cfg


# --- Installed system branding files -------------------------------------------
OS_RELEASE = f"""NAME="{OS_NAME}"
PRETTY_NAME="{OS_NAME} (Arch-based)"
ID=yazan
ID_LIKE=arch
ANSI_COLOR="1;34"
HOME_URL="{LIVE_URL}"
BUILD_ID=rolling
"""

ISSUE = f"{OS_NAME} \\r (\\l)\n"

MOTD = f"""        .--.
       |o_o |
       |:_/ |
      //   \\ \\
     (|     | )
    /'\\_   _/`\\
    \\___)=(___/


  Welcome to {OS_NAME}
  Arch-based. Minimal. Yours.
  Kernel: \\r | Shell: \\s

"""