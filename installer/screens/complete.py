"""Screen 9 -- Installation complete.

Confirmation box with the Tux logo, then Reboot Now or Drop to Shell.
"""

import os
import subprocess
import sys

from core import ui
from core.config import tux


def run(cfg, status):
    if status == "reboot":
        ui.message(
            "Installation complete",
            f"{tux()}\n\n"
            "   [OK] Yazan Linux installed!\n\n"
            "Remove the install media and reboot to boot into\n"
            "your new system. Tux will be waiting.",
        )
        items = [
            ("reboot", "Reboot Now"),
            ("shell", "Drop to Shell"),
        ]
    else:
        ui.message(
            "Installation failed",
            f"{tux()}\n\n"
            "  [WARN] Installation did not finish.\n\n"
            "The console log is saved to /tmp/yazan-install.log.\n"
            "Inspect it, fix the issue and run the installer again.",
        )
        items = [
            ("shell", "Drop to Shell"),
            ("retry", "Run Installer Again"),
        ]

    if status == "reboot":
        items = [
            ("reboot", "Reboot Now"),
            ("shell", "Drop to Shell"),
        ]
    else:
        items = [
            ("shell", "Drop to Shell"),
            ("retry", "Run Installer Again"),
        ]

    tags, cancelled = ui.select(
        "Installation complete",
        f"{tux()}\n\nWhat would you like to do?",
        items, kind=ui.MENU, width=52,
    )
    choice = tags[0] if tags and not cancelled else "shell"
    return choice


def perform(choice):
    if choice == "reboot":
        subprocess.run(["systemctl", "reboot"], check=False)
    elif choice == "retry":
        main_py = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py"
        )
        subprocess.run([sys.executable, main_py], check=False)
    else:
        subprocess.run(["/bin/bash", "-l"], check=False)