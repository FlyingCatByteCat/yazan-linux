"""Screen 1 -- Welcome.

Shows the Tux logo and a friendly greeting, then offers to begin the
guided installation or exit back to the shell.
"""

from core import ui
from core.config import OS_NAME, TAGLINE, VERSION, tux


def run(cfg):
    text = (
        f"{tux()}\n\n\n"
        f"  {OS_NAME} -- guided installer\n"
        f"  {TAGLINE}\n"
        f"  version {VERSION}\n\n"
        f"  This installer walks you through a rolling, minimal\n"
        f"  desktop system. Everything below is yours to choose."
    )
    ui.message("Welcome", text)

    items = [
        ("begin", "Begin Installation"),
        ("exit", "Exit"),
    ]
    tags, cancelled = ui.select(
        "Welcome",
        f"{tux()}\n\nWhat would you like to do?",
        items,
        kind=ui.MENU,
    )
    if cancelled:
        return False
    if tags and tags[0] == "begin":
        return True
    return False