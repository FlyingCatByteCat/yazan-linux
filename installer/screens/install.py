"""Screen 8 -- Guided installation engine.

Partitioning, base system bootstrap, system configuration, desktop
packages, bootloader, branding and finalisation happen here with a live
progress gauge and every command captured to /tmp/yazan-install.log.
"""

import os
import subprocess

from core import chroot as cr, disk as cdisk, pacstrap as ps
from core.config import (
    LOG_FILE, log_error, log_ok, log_warn, tux,
)

TARGET = "/mnt"

BOOTLOADER_PACKAGES = {
    "grub": ["grub", "efibootmgr"],
    "systemd-boot": ["efibootmgr"],
    "refind": ["refind"],
}

DISPLAY_PACKAGES = {
    "xorg": ["xorg-server", "xorg-xinit", "xorg-apps"],
    "wayland": ["wayland", "wayland-utils"],
}

AUDIO_PACKAGES = {
    "pipewire": [
        "pipewire", "pipewire-pulse", "pipewire-audio",
        "wireplumber", "gst-plugin-pipewire", "alsa-utils",
    ],
    "pulseaudio": ["pulseaudio", "pulseaudio-alsa", "alsa-utils", "pavucontrol"],
}

NETWORK_PACKAGES = {
    "NetworkManager": ["networkmanager"],
    "iwd": ["iwd", "dhcpcd"],
    "none": [],
}

NETWORK_SERVICES = {
    "NetworkManager": ["NetworkManager", "systemd-resolved"],
    "iwd": ["iwd", "dhcpcd", "systemd-resolved"],
    "none": [],
}

SHELL_PACKAGES = {
    "bash": [],
    "zsh": ["zsh"],
    "fish": ["fish"],
}


class Gauge:
    """Live progress dialog powered by whiptail --gauge."""

    def __init__(self):
        self.proc = subprocess.Popen(
            ["whiptail", "--clear", "--title", "Installing Yazan Linux",
             "--gauge", f"{tux()}\n\nStarting...", "0", "0", "0"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def update(self, percent, text):
        payload = f"XXX\n{int(percent)}\n{tux()}\n\n{text}\nXXX\n"
        try:
            self.proc.stdin.write(payload.encode("utf-8"))
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError):
            pass

    def finish(self):
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        self.proc.wait()


def _package_plan(cfg):
    comp = cfg.component()
    pkgs = list(comp.get("packages", []))

    bootloader = cfg.bootloader
    if bootloader == "systemd-boot" and not cfg.efi:
        log_warn("systemd-boot requires UEFI; falling back to GRUB.")
        bootloader = "grub"
        cfg.bootloader = "grub"
    if bootloader == "refind" and not cfg.efi:
        log_warn("rEFInd targets UEFI machines; falling back to GRUB.")
        bootloader = "grub"
        cfg.bootloader = "grub"

    pkgs += BOOTLOADER_PACKAGES[bootloader]
    pkgs += DISPLAY_PACKAGES[cfg.display_server]
    pkgs += AUDIO_PACKAGES[cfg.audio]
    pkgs += NETWORK_PACKAGES[cfg.network]
    pkgs += SHELL_PACKAGES[cfg.shell]
    return pkgs


def _service_plan(cfg):
    comp = cfg.component()
    services = list(comp.get("services", []))
    services += NETWORK_SERVICES[cfg.network]
    return services


def _bootstrap(cfg, gauge):
    gauge.update(4, "Preparing install environment...")
    cdisk.unmount_target()

    gauge.update(7, "Partitioning the disk...")
    if cfg.partition_mode == "manual":
        plan = {"disk": cfg.disk, "efi": cfg.efi,
                "root": cfg.manual_root, "boot": cfg.manual_boot}
        if cfg.manual_boot:
            cdisk.mount_manual(cfg.manual_root, cfg.manual_boot)
        else:
            cdisk.mount_manual(cfg.manual_root, None)
    else:
        plan = cdisk.partition_disk(cfg.disk, efi=cfg.efi, wipe=True)
        cdisk.format_and_mount(plan, cfg.filesystem)

    gauge.update(15, ":: pacstrap -K /mnt base linux linux-firmware ...")
    ps.pacstrap_base(TARGET)

    gauge.update(56, "Generating fstab...")
    cdisk.generate_fstab()

    gauge.update(59, "Setting timezone and locale...")
    cr.set_timezone(TARGET, cfg.region, cfg.city)
    cr.set_locale(TARGET, cfg.locale)
    cr.set_hostname(TARGET, cfg.hostname)

    gauge.update(64, "Installing desktop components...")
    pkgs = _package_plan(cfg)
    if pkgs:
        ps.pacman_chroot(pkgs, TARGET)

    gauge.update(72, "Creating users and passwords...")
    cr.set_users(TARGET, cfg.username, cfg.user_password, cfg.root_password)
    cr.set_shell(TARGET, cfg.username, cfg.shell)
    cr.enable_services(TARGET, _service_plan(cfg))
    cr.write_branding(TARGET)
    cr.write_login_scripts(TARGET, cfg.username)

    gauge.update(76, "Regenerating initramfs...")
    cr.mkinitcpio_regenerate(TARGET)

    if cfg.bootloader == "grub":
        cr.install_grub_theme(TARGET)

    gauge.update(82, f"Installing bootloader ({cfg.bootloader})...")
    cr.install_bootloader(TARGET, cfg.efi, cfg.bootloader)

    if cfg.aur_helper != "none":
        gauge.update(90, f"Building {cfg.aur_helper} from source...")
        ps.install_aur_helper(cfg.aur_helper, TARGET)

    gauge.update(96, "Finalising...")
    cdisk.generate_fstab()


def run(cfg):
    try:
        os.path.exists(LOG_FILE) and os.unlink(LOG_FILE)
    except OSError:
        pass

    if not cfg.efi:
        cfg.efi = cdisk.is_efi()

    gauge = Gauge()
    status = "shell"
    try:
        _bootstrap(cfg, gauge)
        gauge.update(100, "Installation complete! Unmounting...")
        cdisk.unmount_target()
        status = "reboot"
        log_ok("Yazan Linux installed successfully.")
    except Exception as exc:  # noqa: BLE001 -- never let the TUI die silently
        log_error(f"Installation error: {exc}")
        try:
            cdisk.unmount_target()
        except Exception:
            pass
    finally:
        gauge.update(100, "Done." if status == "reboot" else "Installation failed.")
        gauge.finish()
    return status