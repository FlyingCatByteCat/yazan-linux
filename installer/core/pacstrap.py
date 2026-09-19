"""Package bootstrap and management helpers.

Wraps pacstrap, arch-chroot pacman and AUR helper bootstrap (yay/paru).
All internal comments reference vanilla Arch tooling; user-facing strings
never mention it.
"""

import os
import subprocess

from core.config import log, log_ok, log_warn
from core.disk import TARGET

BASE_PACKAGES = [
    "base",
    "linux",
    "linux-firmware",
    "linux-headers",
    "base-devel",
    "git",
    "sudo",
    "vim",
    "openssh",
]

LOG = "/tmp/yazan-install.log"


def stream(command, log_file=LOG, cwd=None):
    """Run a command streaming its stdout line-by-line to both the console
    and the install log file."""
    import sys
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    with open(log_file, "a") as fh:
        fh.write(f"$ {command}\n")
    proc = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, cwd=cwd, env=env,
    )
    assert proc.stdout is not None
    with open(log_file, "a") as fh:
        for raw_line in proc.stdout:
            for line in raw_line.splitlines() or [raw_line]:
                if not line.strip():
                    continue
                sys.stdout.write(line + "\n")
                sys.stdout.flush()
                fh.write(line + "\n")
    proc.wait()
    return proc.returncode


def quiet(command, cwd=None):
    proc = subprocess.run(
        command, shell=True, text=True, cwd=cwd,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def pacstrap_base(target=TARGET):
    """Bootstrap the base system with the canonical -K flag."""
    log(f"Installing base system on {target}...")
    cmd = "pacstrap -K {0} {1}".format(target, " ".join(BASE_PACKAGES))
    rc = stream(cmd)
    if rc != 0:
        raise RuntimeError(f"pacstrap failed with code {rc}")
    return rc


def pacman_chroot(packages, target=TARGET):
    """Install packages inside the chroot non-interactively."""
    install = ["pacman", "-S", "--noconfirm", "--needed"]
    cmd = " ".join(install + list(packages))
    rc = stream(f"arch-chroot {target} {cmd}")
    if rc != 0:
        raise RuntimeError(f"pacman install failed with code {rc} (packages: {' '.join(packages)})")
    return rc


def install_aur_helper(name, target=TARGET):
    """Build a yay/paru AUR helper from source inside the chroot."""
    if name not in ("yay", "paru"):
        raise ValueError(f"Unsupported AUR helper: {name}")

    build_deps = {"yay": ["go"], "paru": ["rust"]}
    log(f"Installing AUR helper: {name}")
    pacman_chroot(["git", *build_deps[name]], target=target)

    rc, _ = quiet(
        f"arch-chroot {target} sh -c "
        f"'useradd -m -s /bin/bash builder 2>/dev/null; "
        f"echo \"builder ALL=(ALL) NOPASSWD: ALL\" > /etc/sudoers.d/builder'"
    )
    if rc != 0:
        raise RuntimeError("Failed to prepare builder user")

    build_script = (
        "cd /home/builder && "
        f"rm -rf {name} && "
        f"git clone https://aur.archlinux.org/{name}.git && "
        f"cd {name} && "
        "chown -R builder:builder /home/builder && "
        "su builder -c 'makepkg --noconfirm --skippgpcheck -s'"
    )
    rc = stream(f"arch-chroot {target} sh -c '{build_script}'")
    if rc != 0:
        raise RuntimeError(f"{name} failed to build")

    rc, _ = quiet(
        f"arch-chroot {target} sh -c "
        f"'pacman -U --noconfirm /home/builder/{name}/*.pkg.tar.zst'"
    )
    if rc != 0:
        raise RuntimeError(f"{name} failed to install")

    quiet(
        f"arch-chroot {target} sh -c "
        f"'userdel -r builder 2>/dev/null; rm -f /etc/sudoers.d/builder; rm -rf /home/builder/{name}'"
    )
    log_ok(f"{name} installed")
    return 0


def pacman_keyring(target=TARGET):
    """Refresh keyring in the chroot (needed to trust repo keys on boot)."""
    log("Refreshing package keyring...")
    rc = stream(f"arch-chroot {target} sh -c "
                f"'pacman-key --init && pacman-key --populate'")
    if rc != 0:
        log_warn("Keyring population reported a warning; continuing anyway.")
    return rc