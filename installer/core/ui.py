"""Thin, dependency-free wrapper around whiptail (newt).

Every dialog in the installer goes through this module so that styling
(backtitle, sizing, colour) stays consistent across all screens.
"""

import subprocess

from core.config import OS_NAME, TAGLINE

BTITLE = f"{OS_NAME} -- {TAGLINE}"

MENU = "menu"
CHECKLIST = "checklist"
RADIOLIST = "radiolist"


def _cmd():
    return ["whiptail", "--clear", "--backtitle", BTITLE]


def _visible_height(text):
    lines = len(text.splitlines())
    lines = max(lines, 10)
    return min(30, lines + 6)


def _result(proc):
    out = proc.stdout.read().rstrip("\n")
    return proc.returncode in (1, 255), out


def message(title, text, width=66):
    proc = subprocess.Popen(
        _cmd() + ["--title", title, "--msgbox", text,
                  str(_visible_height(text)), str(width)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    proc.wait()
    return proc.returncode == 0


def yes_no(title, text, default_yes=True):
    args = _cmd()
    if not default_yes:
        args.append("--defaultno")
    args += ["--yesno", title, text, "12", "66"]
    proc = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    proc.wait()
    return proc.returncode == 0


def input_box(title, text, initial="", password=False, width=66):
    tag = "--passwordbox" if password else "--inputbox"
    args = _cmd() + [*tag.split(), title, text, "10", str(width)]
    if initial:
        args.append(initial)
    proc = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    proc.wait()
    cancelled, value = _result(proc)
    if cancelled:
        return True, ""
    return False, value


def select(title, text, items, kind=MENU, width=66):
    """Render a menu, checklist or radiolist.

    `items` is a list of (tag, display_text) tuples. For CHECKLIST and
    RADIOLIST a third element "ON"/"OFF" sets the initial state.
    Returns (tags, cancelled).
    """
    tag = {
        MENU: "--menu",
        CHECKLIST: "--checklist",
        RADIOLIST: "--radiolist",
    }[kind]

    height = _visible_height(text)
    list_height = min(12, max(4, len(items) + 2))
    args = [*tag.split(), title, text, str(height), str(width), str(list_height)]
    for item in items:
        args.append(item[0])
        args.append(item[1])
        if kind in (CHECKLIST, RADIOLIST):
            args.append(item[2] if len(item) > 2 else "OFF")
    proc = subprocess.Popen(
        _cmd() + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    proc.wait()
    cancelled, out = _result(proc)
    if cancelled:
        return [], True
    return out.split(), False


def groom_input(value):
    """Normalise free-form user input (hostname, username)."""
    value = value.strip().replace("\n", "")
    return value.replace(" ", "_")