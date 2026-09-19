"""Screen 4 -- Disk selection and partitioning.

Lists detected disks with sizes, lets the user pick automatic
partitioning (recommended) or a manual layout made with cfdisk, and
chooses the root filesystem (ext4 / btrfs / xfs).
"""

from core import disk, ui
from core.config import tux

FILESYSTEMS = [
    ("ext4", "ext4 -- reliable, mature, general purpose"),
    ("btrfs", "btrfs -- snapshots, compression, subvolumes"),
    ("xfs", "xfs -- high performance for large files"),
]


def _pick_disk(cfg):
    while True:
        disks = disk.list_disks()
        if not disks:
            ui.message(
                "No disks found",
                f"{tux()}\n\nNo disks were detected. Make sure a disk is\n"
                "attached to the machine, then try again.",
            )
            retry, cancelled = ui.select(
                "No disks found",
                "No disks detected.\nTry again or abort?",
                [("retry", "Scan again"), ("abort", "Abort installation")],
                kind=ui.MENU, width=52,
            )
            if cancelled or (retry and retry[0] == "abort"):
                return False
            continue

        items = [(path, f"{path}   ({size})") for path, size in disks]
        tags, cancelled = ui.select(
            "Select disk",
            f"{tux()}\n\nChoose the disk to install onto. Everything on\n"
            "this disk will be erased.",
            items,
            kind=ui.MENU, width=74,
        )
        if cancelled:
            return False
        cfg.disk = tags[0]
        cfg.disk_size = disk.disk_size(tags[0])
        return True


def _pick_mode(cfg):
    items = [
        ("auto", "Auto partition (recommended) -- wipe and partition the disk"),
        ("manual", "Manual via cfdisk -- use your own layout"),
    ]
    tags, cancelled = ui.select(
        "Partitioning",
        f"{tux()}\n\nHow should {cfg.disk} be partitioned?",
        items,
        kind=ui.MENU, width=74,
    )
    if cancelled:
        return False
    cfg.partition_mode = tags[0]
    return True


def _pick_filesystem(cfg):
    items = [(_id, desc) for _id, desc in FILESYSTEMS]
    tags, cancelled = ui.select(
        "Filesystem",
        f"{tux()}\n\nWhich filesystem should root use?",
        items,
        kind=ui.MENU, width=74,
    )
    if cancelled:
        return False
    cfg.filesystem = tags[0]
    return True


def _manual_layout(cfg):
    logical = _logical_partitions(cfg.disk)
    if not logical:
        ui.message("Manual partitioning",
                   f"{tux()}\n\nNo partitions found on {cfg.disk}.\n"
                   "Create a layout first: launch cfdisk, write the table\n"
                   "and quit before continuing.")
        if not _launch_cfdisk(cfg.disk):
            return False
        logical = _logical_partitions(cfg.disk)
    if not logical:
        ui.message("Manual partitioning",
                   "Still no partitions. Aborting manual mode.")
        return False

    root_items = [(p, p) for p in logical]
    tags, cancelled = ui.select(
        "Root partition",
        f"{tux()}\n\nSelect the partition to use as root (/):",
        root_items, kind=ui.MENU, width=52,
    )
    if cancelled:
        return False
    root = tags[0]

    boot = None
    if disk.is_efi():
        boot_items = [(p, p) for p in logical if p != root]
        tags, cancelled = ui.select(
            "EFI partition",
            f"{tux()}\n\nSelect the EFI system partition (mounted at /boot):",
            boot_items, kind=ui.MENU, width=52,
        )
        if cancelled:
            return False
        boot = tags[0]

    cfg.manual_root = root
    cfg.manual_boot = boot
    plan = {"disk": root, "efi": disk.is_efi(), "root": root, "boot": boot}
    disk.confirm_layout(cfg, plan)
    if not ui.yes_no("Manual layout",
                     f"Using root={root}\n\nProceed with this layout?",
                     default_yes=False):
        return False
    return True


def _logical_partitions(disk_path):
    proc = disk.run(f"lsblk -Jpl -o NAME,TYPE {disk_path}", check=False)
    try:
        import json
        data = json.loads(proc.stdout)
        parts = []
        for block in data.get("blockdevices", []):
            def walk(node):
                for child in node.get("children", []) or []:
                    if child.get("type") in ("part", "lvm"):
                        parts.append(child["path"])
                    walk(child)
            walk(block)
        return parts
    except (json.JSONDecodeError, AttributeError):
        return []


def _launch_cfdisk(disk_path):
    import subprocess
    proc = subprocess.run(
        ["cfdisk", disk_path],
    )
    return proc.returncode == 0


def _auto_layout(cfg):
    efi = disk.is_efi()
    if not disk.is_whole_disk(cfg.disk):
        ui.message("Warning",
                   f"{tux()}\n\n{cfg.disk} does not look like a whole disk.\n"
                   "Automatic partitioning expects a whole disk.")
        return False

    plan = disk.partition_disk(cfg.disk, efi=efi, wipe=True)
    disk.confirm_layout(cfg, plan)
    proceed = ui.yes_no(
        "Confirm installation",
        f"Installing to {cfg.disk} requires erasing the entire disk.\n"
        "\nThis cannot be undone. Continue?",
        default_yes=False,
    )
    if not proceed:
        return False
    disk.format_and_mount(plan, cfg.filesystem)
    return True


def run(cfg):
    if not _pick_disk(cfg):
        return False
    if not _pick_mode(cfg):
        return False
    if not _pick_filesystem(cfg):
        return False

    if cfg.partition_mode == "manual":
        return _manual_layout(cfg)
    return _auto_layout(cfg)