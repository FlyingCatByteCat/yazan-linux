"""Disk detection, partitioning, formatting and mounting helpers.

Works with both UEFI (GPT) and legacy BIOS (MBR) machines and supports
ext4, btrfs and xfs root filesystems.
"""

import json
import os
import re
import subprocess

from core.config import log, log_warn

TARGET = "/mnt"

# --- Shell helpers ----------------------------------------------------------------


def run(command, check=True):
    proc = subprocess.run(
        command, shell=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"Command failed ({proc.returncode}): {command}\n{proc.stderr}"
        )
    return proc


# --- Detection ----------------------------------------------------------------------


def is_efi():
    if os.path.isdir("/sys/firmware/efi"):
        return True
    try:
        return run("efivar -l", check=False).returncode == 0
    except OSError:
        return False


def list_disks():
    """Return a list of whole block devices as (path, size_string)."""
    try:
        proc = subprocess.run(
            ["lsblk", "-Jlp", "-o", "NAME,SIZE,TYPE"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        data = json.loads(proc.stdout)
    except (json.JSONDecodeError, subprocess.SubprocessError):
        return []
    disks = []
    for dev in data.get("blockdevices", []):
        if dev.get("type") == "disk":
            disks.append((dev["path"] if dev.get("path") else dev["name"],
                          dev.get("size", "?")))
    return disks


def disk_size(path):
    try:
        proc = subprocess.run(
            ["lsblk", "-Jlp", "-o", "NAME,SIZE", path],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        data = json.loads(proc.stdout)
        for dev in data.get("blockdevices", []):
            return dev.get("size", "?")
    except (json.JSONDecodeError, subprocess.SubprocessError):
        pass
    return "?"


def is_whole_disk(path):
    """Refuse to partition something that is already a partition."""
    try:
        out = subprocess.run(
            ["lsblk", "-Jlp", "-o", "NAME,TYPE", path],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout
        data = json.loads(out)
        for dev in data.get("blockdevices", []):
            return dev.get("type") == "disk"
    except (json.JSONDecodeError, subprocess.SubprocessError):
        pass
    return False


def _part(disk, index):
    """Partition node for (disk, index). Handles nvme/mmc/loop devices."""
    if re.search(r"\d$", disk):
        return f"{disk}p{index}"
    return f"{disk}{index}"


# --- Partitioning ----------------------------------------------------------------------


def _zap(disk):
    """Remove old partition table so parted starts from a clean state."""
    proc = run(
        f"wipefs -a {disk} 2>/dev/null; "
        f"sgdisk --zap-all {disk} 2>/dev/null; "
        f"dd if=/dev/zero of={disk} bs=1M count=1 conv=fsync status=none 2>/dev/null",
        check=False,
    )
    run(f"partprobe {disk}", check=False)
    return proc


def partition_disk(disk, efi, wipe=True):
    """Partition a whole disk. Returns a dict describing the result."""
    if wipe:
        _zap(disk)

    if efi:
        # GPT: 1 GiB EFI system partition, remainder for root.
        run(f"parted -s {disk} mklabel gpt")
        run(f"parted -s {disk} mkpart YazanLinux-ESP fat32 1MiB 1025MiB")
        run(f"parted -s {disk} set 1 esp on")
        run(f"parted -s {disk} mkpart YazanLinux-root ext4 1025MiB 100%")
        return {
            "disk": disk,
            "efi": True,
            "boot": _part(disk, 1),
            "root": _part(disk, 2),
        }
    # MBR: single root partition with the boot flag.
    run(f"parted -s {disk} mklabel msdos")
    run(f"parted -s {disk} mkpart primary ext4 1MiB 100%")
    run(f"parted -s {disk} set 1 boot on")
    return {
        "disk": disk,
        "efi": False,
        "boot": None,
        "root": _part(disk, 1),
    }


# --- Formatting & mounting ---------------------------------------------------------------


def _mkfs(part, fstype):
    if fstype == "ext4":
        run(f"mkfs.ext4 -F -L YAZANROOT {part}")
    elif fstype == "xfs":
        run(f"mkfs.xfs -f -L YAZANROOT {part}")
    elif fstype == "btrfs":
        run(f"mkfs.btrfs -f -L YAZANROOT {part}")
    else:
        raise RuntimeError(f"Unsupported filesystem: {fstype}")


def format_and_mount(plan, fstype):
    """Format and mount the partitions described by `plan` onto TARGET."""
    run(f"mkdir -p {TARGET}")

    if plan["efi"]:
        _mkfs(plan["root"], fstype)
        run(f"mount {plan['root']} {TARGET}")
        run(f"mkdir -p {TARGET}/boot")
        run(f"mkfs.fat -F32 -n YAZANBOOT {plan['boot']}")
        run(f"mount {plan['boot']} {TARGET}/boot")
    else:
        _mkfs(plan["root"], fstype)
        run(f"mount {plan['root']} {TARGET}")


def generate_fstab():
    run(f"genfstab -U {TARGET} > {TARGET}/etc/fstab")
    with open(f"{TARGET}/etc/fstab", "a") as fh:
        fh.write("# yazan-linux -- generated fstab\n")


# --- Manual partition support ----------------------------------------------------------------


def mount_manual(root, boot=None):
    run(f"mkdir -p {TARGET}")
    run(f"mount {root} {TARGET}")
    if boot:
        run(f"mkdir -p {TARGET}/boot")
        run(f"mount {boot} {TARGET}/boot")
    generate_fstab()


def unmount_target():
    run(f"umount -R {TARGET}", check=False)
    run(f"swapoff -a", check=False)


def confirm_layout(cfg, plan):
    """Print a human summary of where the installer is about to write."""
    root = plan["root"]
    size = disk_size(plan["disk"])
    log_warn("About to destroy everything on the selected disk!")
    log(f"Disk        : {plan['disk']} ({size})")
    if plan["efi"]:
        log(f"EFI system  : {plan['boot']} (FAT32, 1 GiB)")
        log(f"Root        : {root} ({cfg.filesystem}, rest of disk)")
    else:
        log(f"Root        : {root} (MBR boot flag, {cfg.filesystem})")