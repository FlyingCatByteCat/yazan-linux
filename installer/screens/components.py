"""Screen 5 -- Component selection.

Guided radiolist choices for desktop environment, bootloader, display
server, audio, network, shell and AUR helper.
"""

from core import ui
from core.config import list_components, load_component, tux

DISPLAY_SERVERS = [
    ("wayland", "Wayland -- modern compositor protocol"),
    ("xorg", "Xorg -- classic X11 server"),
]

AUDIO_STACKS = [
    ("pipewire", "PipeWire -- modern unified audio (recommended)"),
    ("pulseaudio", "PulseAudio -- traditional audio server"),
]

NETWORK_STACKS = [
    ("NetworkManager", "NetworkManager -- automatic wired + wireless"),
    ("iwd", "iwd + dhcpcd -- lightweight wireless + wired"),
    ("none", "None -- configure networking by hand"),
]

SHELLS = [
    ("bash", "bash -- default"),
    ("zsh", "zsh -- power user shell"),
    ("fish", "fish -- friendly interactive shell"),
]

AUR_HELPERS = [
    ("none", "None -- no AUR helper"),
    ("paru", "paru -- AUR helper in Rust"),
    ("yay", "yay -- AUR helper in Go"),
]


def _component_items():
    items = []
    for cid in list_components():
        comp = load_component(cid)
        items.append((cid, f"{comp['name']} -- {comp['description']}"))
    return items


def _select(cfg, title, label, items, kind=ui.RADIOLIST, width=74):
    tags, cancelled = ui.select(
        title,
        f"{tux()}\n\n{label}",
        items,
        kind=kind,
        width=width,
    )
    if cancelled:
        return None
    return tags[0] if tags else None


def _pick_desktop(cfg):
    items = []
    for cid in list_components():
        comp = load_component(cid)
        items.append((cid, f"{comp['name']} -- {comp['description']}"))
    choice = _select(cfg, "Desktop environment",
                     "Pick your desktop (exactly one):", items)
    if choice is None:
        return False
    cfg.desktop_id = choice
    return True


def _pick_bootloader(cfg):
    items = [
        ("grub", "GRUB -- recommended, full-featured"),
        ("systemd-boot", "systemd-boot -- minimal UEFI loader"),
        ("refind", "rEFInd -- multi-boot manager"),
    ]
    choice = _select(cfg, "Bootloader", "Pick your bootloader:", items)
    if choice is None:
        return False
    cfg.bootloader = choice
    return True


def _pick_display(cfg):
    choice = _select(cfg, "Display server", "Pick the display backend:",
                     [(k, v) for k, v in DISPLAY_SERVERS])
    if choice is None:
        return False
    cfg.display_server = choice
    return True


def _pick_audio(cfg):
    choice = _select(cfg, "Audio", "Pick the audio stack:",
                     [(k, v) for k, v in AUDIO_STACKS])
    if choice is None:
        return False
    cfg.audio = choice
    return True


def _pick_network(cfg):
    choice = _select(cfg, "Network", "Pick the network manager:",
                     [(k, v) for k, v in NETWORK_STACKS])
    if choice is None:
        return False
    cfg.network = choice
    return True


def _pick_shell(cfg):
    choice = _select(cfg, "Shell", "Pick the default user shell:",
                     [(k, v) for k, v in SHELLS])
    if choice is None:
        return False
    cfg.shell = choice
    return True


def _pick_aur(cfg):
    choice = _select(cfg, "AUR helper",
                     "Do you want an AUR helper installed?",
                     [(k, v) for k, v in AUR_HELPERS])
    if choice is None:
        return False
    cfg.aur_helper = choice
    return True


def run(cfg):
    steps = [
        _pick_desktop, _pick_bootloader, _pick_display,
        _pick_audio, _pick_network, _pick_shell, _pick_aur,
    ]
    for step in steps:
        if not step(cfg):
            return False
    return True