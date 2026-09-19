"""System configuration helpers executed inside the installed chroot.

Covers timezone, locale, hostname, users, sudo, services, bootloader,
the GRUB theme and the final branding files that make the installed
system identify itself as Yazan Linux.
"""

import json
import os
import shlex
import subprocess

from core.config import (
    OS_RELEASE, ISSUE, MOTD, log, log_ok, log_warn,
)


def run(target, command):
    proc = subprocess.run(
        f"arch-chroot {target} bash -c {command!r}",
        shell=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return proc.returncode, f"{proc.stdout}{proc.stderr}".strip()


def sh(target, command):
    rc, out = run(target, command)
    if rc != 0:
        raise RuntimeError(
            f"chroot command failed ({rc}): {command}\n{out}"
        )
    return out


# --- Configuration ---------------------------------------------------------------


def set_timezone(target, region, city):
    zone = f"{region}/{city}"
    if not os.path.isfile(f"{target}/usr/share/zoneinfo/{zone}"):
        log_warn(f"Zone file not found for {zone}; keeping default.")
        return
    os.makedirs(f"{target}/etc", exist_ok=True)
    os.symlink(f"/usr/share/zoneinfo/{zone}", f"{target}/etc/localtime")
    sh(target, "hwclock --systohc")


def set_locale(target, locale_code):
    locale_gen = locale_code.split(".")[0]
    gen_path = f"{target}/etc/locale.gen"
    if os.path.exists(gen_path):
        with open(gen_path, "r") as fh:
            lines = fh.readlines()
        changed = False
        for i, line in enumerate(lines):
            if line.startswith(f"#{locale_code}") or line.startswith(locale_code):
                if not line.startswith(" "):
                    lines[i] = line.lstrip("#")
                    changed = True
        if changed:
            with open(gen_path, "w") as fh:
                fh.writelines(lines)
    sh(target, "locale-gen")
    with open(f"{target}/etc/locale.conf", "w") as fh:
        fh.write(f"LANG={locale_code}\n")
    keymap = "us"
    with open(f"{target}/etc/vconsole.conf", "w") as fh:
        fh.write(f"KEYMAP={keymap}\n")


def set_hostname(target, hostname):
    with open(f"{target}/etc/hostname", "w") as fh:
        fh.write(hostname + "\n")
    hosts = (
        "127.0.0.1   localhost\n"
        "::1         localhost\n"
        f"127.0.1.1   {hostname}.local {hostname}\n"
    )
    with open(f"{target}/etc/hosts", "w") as fh:
        fh.write(hosts)


def set_password(target, user, password):
    escaped = password.replace("'", "'\\''")
    sh(target, f"printf '%s\\n' {shlex.quote(f'{user}:{password}')} | chpasswd")


def set_users(target, username, user_password, root_password):
    user = shlex.quote(username)
    sh(target, f"useradd -m -G wheel -s /bin/bash {user}")
    set_password(target, username, user_password)
    set_password(target, "root", root_password)

    sudoers = f"{target}/etc/sudoers"
    with open(sudoers, "r") as fh:
        content = fh.read()
    if "%wheel ALL=(ALL:ALL) ALL" in content and "# %wheel" in content:
        content = content.replace("# %wheel ALL=(ALL:ALL) ALL",
                                  "%wheel ALL=(ALL:ALL) ALL")
        with open(sudoers, "w") as fh:
            fh.write(content)
    else:
        with open(f"{target}/etc/sudoers.d/99-yazan", "w") as fh:
            fh.write("%wheel ALL=(ALL) ALL\n")
        sh(target, "chmod 440 /etc/sudoers.d/99-yazan")


def set_shell(target, username, shell_name):
    shell_map = {"bash": "/bin/bash", "zsh": "/bin/zsh", "fish": "/bin/fish"}
    shell = shell_map.get(shell_name, "/bin/bash")
    sh(target, f"chsh -s {shell} {username}")


def enable_services(target, services):
    if not services:
        return
    if "systemd-resolved" in services:
        sh(target, "systemctl enable systemd-resolved")
        os.symlink(
            "/run/systemd/resolve/stub-resolv.conf",
            f"{target}/etc/resolv.conf",
        )
    for service in services:
        if service == "systemd-resolved":
            continue
        sh(target, f"systemctl enable {service}")


def set_vconsole_help():
    pass  # placeholder retained for symmetry; vconsole set in set_locale


# --- Bootloader -------------------------------------------------------------------


def install_grub(target, efi):
    if efi:
        sh(target, "grub-install --target=x86_64-efi "
                   "--efi-directory=/boot --bootloader-id=YAZAN")
    else:
        devices = _grub_devices()
        for dev in devices:
            sh(target, f"grub-install --target=i386-pc {dev}")
    sh(target, "grub-mkconfig -o /boot/grub/grub.cfg")


def _grub_devices():
    try:
        out = subprocess.run(
            ["lsblk", "-Jpl", "-o", "NAME,TYPE"],
            text=True, stdout=subprocess.PIPE,
        ).stdout
        import json
        data = json.loads(out)
        devs = []
        for block in data.get("blockdevices", []):
            for dev in block.get("children", []) if block.get("children") else []:
                if dev.get("type") == "disk":
                    devs.append(dev["path"])
        return devs
    except Exception:
        return []


def install_systemd_boot(target, root_uuid):
    sh(target, "bootctl --path=/boot install")
    with open(f"{target}/boot/loader/loader.conf", "w") as fh:
        fh.write("default yazan\n"
                 "timeout 5\n"
                 "console-mode max\n")
    with open(f"{target}/boot/loader/entries/yazan.conf", "w") as fh:
        fh.write("title Yazan Linux\n"
                 "linux /vmlinuz-linux\n"
                 "initrd /initramfs-linux.img\n"
                 f"options root=UUID={root_uuid} rw\n")
    with open(f"{target}/boot/loader/entries/yazan-fallback.conf", "w") as fh:
        fh.write("title Yazan Linux (recovery)\n"
                 "linux /vmlinuz-linux\n"
                 "initrd /initramfs-linux-fallback.img\n"
                 f"options root=UUID={root_uuid} rw\n")


def install_refind(target):
    sh(target, "refind-install 2>/dev/null || "
               "refind-install --usedefault /dev/__PLACEHOLDER__ 2>/dev/null")


def root_uuid(target):
    try:
        out = subprocess.run(
            ["lsblk", "-Jpl", "-o", "MOUNTPOINTS,UUID"],
            text=True, stdout=subprocess.PIPE,
        ).stdout
        data = json.loads(out)
        for block in data.get("blockdevices", []):
            for dev in block.get("children", []) if block.get("children") else []:
                mounts = dev.get("mountpoints", [])
                if mounts and f"{target}/" in [m or "" for m in mounts]:
                    return dev.get("uuid", "")
    except Exception:
        pass
    return ""


def install_bootloader(target, efi, which):
    log(f"Installing bootloader: {which}")
    if which == "grub":
        install_grub(target, efi)
    elif which == "systemd-boot":
        install_systemd_boot(target, root_uuid(target))
    elif which == "refind":
        install_refind(target)
    else:
        raise ValueError(f"Unknown bootloader: {which}")
    log_ok("Bootloader installed")


# --- GRUB theme ---------------------------------------------------------------------


def install_grub_theme(target):
    from core.grub_theme import generate_theme
    generate_theme(f"{target}/boot/grub/themes/yazan")
    with open(f"{target}/etc/default/grub", "r") as fh:
        grub_cfg = fh.read()
    additions = {
        "GRUB_DEFAULT": "0",
        "GRUB_TIMEOUT": "5",
        "GRUB_DISTRIBUTOR": '"Yazan Linux"',
        "GRUB_GFXMODE": "1280x720,auto",
        "GRUB_THEME": '"/boot/grub/themes/yazan/theme.txt"',
    }
    for key, value in additions.items():
        for line in grub_cfg.splitlines():
            if line.startswith(f"{key}="):
                grub_cfg = grub_cfg.replace(line, f"{key}={value}")
                break
        else:
            grub_cfg += f"{key}={value}\n"
    with open(f"{target}/etc/default/grub", "w") as fh:
        fh.write(grub_cfg)


# --- Branding files ---------------------------------------------------------------


def write_branding(target):
    with open(f"{target}/etc/os-release", "w") as fh:
        fh.write(OS_RELEASE)
    with open(f"{target}/etc/issue", "w") as fh:
        fh.write(ISSUE)
    with open(f"{target}/etc/motd", "w") as fh:
        fh.write(MOTD)
    try:
        os.unlink(f"{target}/etc/lsb-release")
    except OSError:
        pass
    with open(f"{target}/etc/lsb-release", "w") as fh:
        fh.write("DISTRIB_ID=YazanLinux\n"
                 "DISTRIB_RELEASE=rolling\n"
                 "DISTRIB_DESCRIPTION=\"Yazan Linux (Arch-based)\"\n")


def write_login_scripts(target, username):
    """Splash + friendly first-login helpers in the user's shell rc."""
    rc = f"{target}/home/{username}/.bashrc"
    if os.path.exists(rc):
        with open(rc, "a") as fh:
            fh.write("\n# Yazan Linux MOTD\n")
            fh.write('if [ -f /etc/motd ]; then cat /etc/motd; fi\n')


def mkinitcpio_regenerate(target):
    sh(target, "mkinitcpio -P")