"""Screen 6 -- User setup.

Hostname, primary user (username + password) and root password.
"""

import re

from core import ui
from core.config import tux


def _hostname(cfg):
    cancelled, value = ui.input_box(
        "Hostname", f"{tux()}\n\nSet the machine hostname:",
        initial=cfg.hostname,
    )
    if cancelled:
        return False
    value = ui.groom_input(value)
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9-]{0,62}$", value):
        ui.message("Invalid hostname",
                   f"{tux()}\n\nHostnames must start with a letter or digit\n"
                   "and use only letters, digits and hyphens.")
        return False
    cfg.hostname = value
    return True


def _username(cfg):
    cancelled, value = ui.input_box(
        "Username",
        f"{tux()}\n\nChoose a username for the primary account:",
    )
    if cancelled:
        return False
    value = ui.groom_input(value)
    if not re.match(r"^[a-z_][a-z0-9_-]{0,31}$", value):
        ui.message("Invalid username",
                   f"{tux()}\n\nUsernames must be lowercase and start\n"
                   "with a letter or underscore.")
        return False
    cfg.username = value
    return True


def _ask_password(title, label):
    while True:
        cancelled, pw1 = ui.input_box(
            title, f"{tux()}\n\n{label}", password=True,
        )
        if cancelled:
            return None
        if len(pw1) < 6:
            ui.message(title, f"{tux()}\n\nPasswords must be at least\n6 characters long.")
            continue
        cancelled, pw2 = ui.input_box(
            title, f"{tux()}\n\n{label}\n\nRe-enter the password to confirm:",
            password=True,
        )
        if cancelled:
            return None
        if pw1 != pw2:
            ui.message(title, f"{tux()}\n\nPasswords do not match. Try again.")
            continue
        return pw1


def run(cfg):
    if not _hostname(cfg):
        return False
    if not _username(cfg):
        return False

    user_pw = _ask_password("User password", "Set the password for the primary account:")
    if user_pw is None:
        return False
    root_pw = _ask_password("Root password", "Set the root (administrator) password:")
    if root_pw is None:
        return False

    cfg.user_password = user_pw
    cfg.root_password = root_pw
    return True