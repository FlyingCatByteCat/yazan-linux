"""Screen 7 -- Installation summary.

Renders a review table of every choice and offers Install / Go Back /
Abort. Returns 'install', 'back' or 'abort'.
"""

from core import ui
from core.config import OS_NAME, load_component, tux


def _format_value(cfg, key, value):
    if key == "desktop_id":
        try:
            return load_component(value)["name"]
        except OSError:
            return value
    if key == "disk":
        return f"{value} ({cfg.filesystem}, {cfg.partition_mode})"
    if key == "efi":
        return "UEFI" if value else "BIOS"
    if key == "region":
        return f"{cfg.region}/{cfg.city}"
    if key in ("user_password", "root_password"):
        return "••••••••"
    if key == "username":
        return value or "(not set)"
    if key == "aur_helper":
        return value.capitalize() if value != "none" else "none"
    if key == "display_server":
        return value.capitalize()
    if key == "bootloader":
        return value
    return value


def _summary_text(cfg):
    entries = [
        ("Disk", _format_value(cfg, "disk", cfg.disk)),
        ("DE", _format_value(cfg, "desktop_id", cfg.desktop_id)),
        ("Bootloader", _format_value(cfg, "bootloader", cfg.bootloader)),
        ("Display", _format_value(cfg, "display_server", cfg.display_server)),
        ("Audio", _format_value(cfg, "audio", cfg.audio)),
        ("Network", _format_value(cfg, "network", cfg.network)),
        ("Shell", _format_value(cfg, "shell", cfg.shell)),
        ("AUR Helper", _format_value(cfg, "aur_helper", cfg.aur_helper)),
        ("Firmware", _format_value(cfg, "efi", cfg.efi)),
        ("Locale", cfg.locale),
        ("Zone", _format_value(cfg, "region", cfg.region)),
        ("User", _format_value(cfg, "username", cfg.username)),
        ("Hostname", cfg.hostname),
    ]
    lines = [f"{OS_NAME} -- Summary", "─" * 44]
    for name, value in entries:
        lines.append(f" {name:<11}: {value}")
    lines.append("─" * 44)
    return "\n".join(lines)


def run(cfg):
    cfg.efi = _detect_efi(cfg)
    text = _summary_text(cfg)
    ui.message("Installation summary", f"{tux()}\n\n{text}")

    items = [
        ("install", "Install"),
        ("back", "Go Back"),
        ("abort", "Abort"),
    ]
    tags, cancelled = ui.select(
        "Installation summary",
        f"{tux()}\n\nEverything below is what will be installed.\n"
        "Go back to change anything.",
        items, kind=ui.MENU, width=74,
    )
    if cancelled or (tags and tags[0] == "abort"):
        return "abort"
    if tags and tags[0] == "back":
        return "back"
    return "install"


def _detect_efi(cfg):
    try:
        import os
        if os.path.isdir("/sys/firmware/efi"):
            return True
        from core import disk
        return disk.is_efi()
    except OSError:
        return cfg.efi