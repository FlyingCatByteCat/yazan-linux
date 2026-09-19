# Yazan Linux

> **Yazan Linux** — Arch-based. Minimal. Yours.
> Tagline: *"The Arch way, your way."*

Yazan Linux is a rolling, minimalist distribution built on the Arch Linux
way — same base, same package manager, same terminal-first philosophy —
with a friendly, guided text-mode installer that carries Tux the Linux
penguin on every screen.

No GTK. No Qt. No GUI. Pure terminal.

---

## Features

- Boots straight into a **guided TUI installer** (whiptail/newt) from the
  live ISO — no manual bootstrapping required.
- Uses the exact same foundations as vanilla Arch: `pacstrap -K`,
  `arch-chroot`, `mkinitcpio`, `genfstab`, GRUB/systemd-boot/rEFInd.
- Blue-accent (#1793D1) Tux branding on every dialog and every console line.
- Destructive-proof with a confirmation before anything is erased and a
  live `[OK] / [*] / [ERROR] / [WARN]` log convention throughout.
- Desktops: KDE Plasma, GNOME, XFCE, Hyprland, i3, Sway, Openbox or pure TTY.
- Bootloaders: GRUB (with a custom black + Tux + blue GRUB theme),
  systemd-boot (minimal EFI), rEFInd.
- One-command ISO build via `build.sh` + `mkarchiso` (works on a rolling
  host or inside a podman/docker container).

## Project layout

```text
yazan-linux/
├── installer/
│   ├── main.py                  # boot splash + installer flow
│   ├── screens/                 # one module per installation step
│   │   ├── welcome.py           #   Screen 1
│   │   ├── locale.py            #   Screen 2 + 3 (language / timezone)
│   │   ├── disk.py              #   Screen 4 (disks, layout, filesystem)
│   │   ├── components.py        #   Screen 5 (DE, bootloader, audio, ...)
│   │   ├── user.py              #   Screen 6 (hostname + accounts)
│   │   ├── summary.py           #   Screen 7 (review everything)
│   │   ├── install.py           #   Screen 8 (live progress gauge)
│   │   └── complete.py          #   Screen 9 (reboot / shell)
│   ├── core/
│   │   ├── config.py            #   styling constants + InstallConfig + branding
│   │   ├── ui.py                #   whiptail wrapper
│   │   ├── disk.py              #   lsblk/parted/mkfs/mount logic
│   │   ├── pacstrap.py          #   pacstrap + pacman + AUR helper builds
│   │   ├── chroot.py            #   locale/timezone/users/services/bootloader
│   │   └── grub_theme.py        #   pure-Python PNG logo + GRUB theme.txt
│   ├── configs/                 # per-desktop package JSON
│   │   ├── kde.json  gnome.json  xfce.json  hyprland.json
│   │   ├── i3.json  sway.json  openbox.json  none.json
│   └── assets/
│       ├── tux.txt              # Tux ASCII logo (used everywhere)
│       └── banner.txt           # "YAZAN L I N U X" figlet banner
├── airootfs/                    # live ISO overlay
│   ├── etc/systemd/system/yazan-installer.service
│   ├── etc/systemd/system/multi-user.target.wants/yazan-installer.service
│   └── etc/  (os-release, issue, motd for the live media)
├── profiledef.sh                # mkarchiso profile
├── packages.x86_64              # live-media packages
├── pacman.conf                  # live-media pacman config
├── build.sh                     # one-command ISO build
└── README.md
```

## Building the ISO

Requirements: a machine able to run (or a podman/docker daemon capable of
running) Linux, root access, and network access to the package mirrors.

```sh
./build.sh              # builds in a podman/docker container (recommended)
./build.sh --local      # uses the host mkarchiso
```

The resulting ISO lands at `out/yazan-linux-1.0.0-x86_64.iso`.

### Build recipe (manual, on a rolling host)

```sh
pacman -S --needed archiso
# write the profile to /etc/archiso/configs/yazan-linux or edit in place
mkarchiso -v -w ./work -o ./out .
```

Known good disk image: bioses, UEFI, and their fallbacks are produced by
`mkarchiso` (see `bootmodes` in `profiledef.sh`). `xorrisofs`/`grub`
requirements are pulled in automatically.

## Using the installer

Boot the ISO on a target machine (UEFI or BIOS). The **Yazan Linux** boot
splash appears, followed by the guided flow:

1. **Welcome** — Tux greets you; choose *Begin Installation*.
2. **Language + Timezone** — pick a locale, then a region / city
   (a `tzselect`-style drill-down backed by the live `/usr/share/zoneinfo`).
3. **Disk** — every detected disk is listed with its size. Choose *Auto
   partition* (recommended) or *Manual via cfdisk*, then the root filesystem
   (ext4 / btrfs / xfs).
4. **Components** — guided radio lists: desktop environment, bootloader,
   display server, audio stack, network manager, shell and AUR helper.
5. **User setup** — hostname, primary account, passwords (with confirm).
6. **Summary** — review everything; *Install / Go Back / Abort*.
7. **Progress** — live gauge with Tux; every command is captured to
   `/tmp/yazan-install.log`.
8. **Complete** — *[OK] Yazan Linux installed!* Choose *Reboot Now* or
   *Drop to Shell*.

Shortcuts during install: press `S` at the boot splash to drop to a root
shell; `Ctrl+C` aborts back to the prompt.

### What the installer does under the hood

1. Detects UEFI/BIOS, wipes and partitions the chosen disk
   (GPT + 1 GiB ESP, or MBR boot flag), formats root (ext4/btrfs/xfs) and
   mounts under `/mnt`.
2. `pacstrap -K /mnt base linux linux-firmware base-devel git sudo vim openssh`
3. `genfstab -U /mnt > /mnt/etc/fstab`
4. In the chroot: timezone symlink + `hwclock --systohc`, `locale-gen`,
   hostname/hosts, user + wheel + sudoers, `chpasswd`, `mkinitcpio -P`.
5. Installs the selected desktop + components per `configs/*.json`.
6. Installs the bootloader and, for GRUB, the custom **Yazan Linux GRUB
   theme** (generated PNG logo of Tux + blue-accent menu, written to
   `/boot/grub/themes/yazan/theme.txt`).
7. (Optional) builds yay/paru from the AUR with a throwaway `builder` user.
8. Writes branding: `/etc/os-release`, `/etc/issue`, `/etc/motd`. See below.

## Branding

### GRUB theme

`installer/core/grub_theme.py` renders the Tux logo to a PNG using only the
Python standard library, then writes a GRUB theme:

- black desktop background,
- Tux logo centered above the boot menu,
- menu entries in the Arch blue accent `#1793D1`,
- selected entry in white.

`/etc/default/grub` is also tuned (`GRUB_THEME`, `GRUB_DISTRIBUTOR="Yazan
Linux"`, `GRUB_TIMEOUT=5`) so menu entries read **Yazan Linux** and the
fallback kernel appears as **Yazan Linux (recovery)** in the advanced
submenu. Because this is a rolling, base-identical system, the recovery
entry is the standard `linux` fallback initramfs.

### Installed system

`/etc/os-release`:

```ini
NAME="Yazan Linux"
PRETTY_NAME="Yazan Linux (Arch-based)"
ID=yazan
ID_LIKE=arch
ANSI_COLOR="1;34"
HOME_URL="https://yazanlinux.org"
BUILD_ID=rolling
```

`/etc/issue`: `Yazan Linux \r (\l)`

First login shows the Tux MOTD plus kernel and shell information.

## Customising

- Add a desktop: drop a new `installer/configs/<id>.json` with `name`,
  `description`, `packages` and `services`, then list `<id>` in
  `list_components()` in `core/config.py`.
- Change accents: edit the ANSI blue triple and `#1793D1` in
  `core/config.py` / `core/grub_theme.py`.
- Tweak package lists per component in `screens/install.py`.

## Styling contract

Enforced on **every** screen and output line:

| Element        | Value                     |
|----------------|---------------------------|
| Background     | black                     |
| Accent         | Arch blue `#1793D1`       |
| Text           | white                     |
| Box borders    | single line `┌─┐│└┘`     |
| `[OK]`         | green                     |
| `[*]`          | blue                      |
| `[ERROR]`      | red                       |
| `[WARN]`       | yellow                    |
| Emoji          | none (never)              |
| GUI            | none — pure terminal      |

## License

Yazan Linux is free software. The installer is distributed under the MIT
license; the distribution itself follows the same licenses as the upstream
packages it ships.