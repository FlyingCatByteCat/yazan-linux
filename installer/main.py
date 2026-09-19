#!/usr/bin/env python3
"""Yazan Linux -- friendly guided installer with Tux on every screen.

Pure Python 3 + whiptail. No GTK, no Qt, no GUI: just the terminal.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import (
    BOOT_CONTINUE, BOOT_SHELL, InstallConfig, VERSION,
    banner, log_ok, tux,
)

from screens import (
    complete, components, disk, install, locale, summary, user, welcome,
)


def _ensure_root():
    if os.geteuid() != 0:
        sys.stderr.write(
            "[ERROR] Yazan Linux installer must run as root. Try: sudo python3 main.py\n"
        )
        sys.exit(1)


def splash():
    """Boot splash: black screen, blue accents, Tux + banner centered."""
    esc = "\033["
    blue = esc + "38;2;23;147;209m"      # Accent color #1793D1
    bright = esc + "1;38;2;96;200;255m"  # lighter blue for highlights
    reset = esc + "0m"

    lines = []
    lines.append("")
    for line in tux().splitlines():
        lines.append(f"{blue}          {line}{reset}")
    lines.append("")
    for line in banner().splitlines():
        lines.append(f"{blue}  {line}{reset}")
    lines.append(f"{bright}            L I N U X{reset}")
    lines.append(f"{bright}     Arch-based. Minimal. Yours.{reset}")
    lines.append(f"{bright}            v{VERSION}{reset}")
    lines.append("")
    lines.append(f"{blue}  [ Press ENTER to begin installation ]{reset}")
    lines.append(f"{blue}  [ Press (S) to drop to shell        ]{reset}")
    lines.append("")

    try:
        rows, cols = os.get_terminal_size()
        width = cols
    except OSError:
        width = 80

    for line in lines:
        pad = max(0, (width - _visible_len(line)) // 2)
        print(" " * pad + line)


def _visible_len(line):
    ansi = False
    count = 0
    for ch in line:
        if ch == "\033":
            ansi = True
        elif ansi:
            if ch == "m":
                ansi = False
        else:
            count += 1
    return count


def _boot_key():
    try:
        raw = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    if raw.startswith("s"):
        return BOOT_SHELL
    return BOOT_CONTINUE


def installer_flow(cfg):
    if not welcome.run(cfg):
        return "exit"
    if not locale.run(cfg):
        return "exit"
    if not disk.run(cfg):
        return "exit"
    while True:
        if not components.run(cfg):
            return "exit"
        while True:
            if not user.run(cfg):
                return "exit"
            decision = summary.run(cfg)
            if decision == "install":
                status = install.run(cfg)
                return complete.run(cfg, status)
            if decision == "abort":
                return "exit"


def main():
    _ensure_root()
    while True:
        splash()
        choice = _boot_key()
        if choice == BOOT_SHELL:
            log_ok("Dropping to a root shell. Type exit to return to the installer.")
            subprocess.run(["/bin/bash", "-l"], check=False)
            continue

        cfg = InstallConfig.load()
        try:
            final = installer_flow(cfg)
        except KeyboardInterrupt:
            print()
            final = "exit"
        cfg.save()

        if final == "reboot":
            log_ok("Rebooting into Yazan Linux. Remove the install media!")
            subprocess.run(["systemctl", "reboot"], check=False)
            return
        if final == "retry":
            log_ok("Restarting the installer.")
            continue
        if final == "shell":
            log_ok("Dropping to a root shell. Type exit to return to the installer.")
            subprocess.run(["/bin/bash", "-l"], check=False)
            continue
        return


if __name__ == "__main__":
    main()