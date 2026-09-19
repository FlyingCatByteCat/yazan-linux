#!/usr/bin/env bash
#
# Yazan Linux -- build script for the live ISO.
#
# Stages the guided installer + live branding into the airootfs overlay,
# then builds the bootable ISO with mkarchiso.
#
# Usage:
#   ./build.sh              default: run in a container (fallback to local)
#   ./build.sh --local      build with the host mkarchiso
#   ./build.sh --isolated   build inside an already-prepared container

set -euo pipefail

NC=$'\033[0m'
BLUE=$'\033[38;2;23;147;209m'   # Arch blue #1793D1
GREEN=$'\033[0;32m'
RED=$'\033[0;31m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AIROOTFS="$ROOT_DIR/airootfs"
INSTALLER_DEST="$AIROOTFS/etc/yazan/installer"
OUT_DIR="$ROOT_DIR/out"
WORK_DIR="$ROOT_DIR/work"
ISO_NAME="yazan-linux-1.0.0-x86_64.iso"

info() { printf '%s[*]%s %s\n' "$BLUE" "$NC" "$*"; }
ok()   { printf '%s[OK]%s %s\n' "$GREEN" "$NC" "$*"; }
fail() { printf '%s[ERROR]%s %s\n' "$RED" "$NC" "$*" >&2; exit 1; }

require_root() {
    [[ "$(id -u)" -eq 0 ]] || fail "build.sh must be run as root."
}

stage_installer() {
    info "Staging the guided installer into airootfs..."
    rm -rf "$INSTALLER_DEST"
    mkdir -p "$(dirname "$INSTALLER_DEST")"
    if command -v rsync >/dev/null 2>&1; then
        rsync -a --exclude '__pycache__' "$ROOT_DIR/installer/" "$INSTALLER_DEST/"
    else
        cp -r "$ROOT_DIR/installer/." "$INSTALLER_DEST/"
    fi
    chmod 755 "$INSTALLER_DEST/main.py"
    chmod 644 "$INSTALLER_DEST/assets/tux.txt" "$INSTALLER_DEST/assets/banner.txt"
    ok "Installer staged at /etc/yazan/installer in the live image."
}

clean_work() {
    [[ -d "$WORK_DIR" ]] && rm -rf "$WORK_DIR"
    mkdir -p "$WORK_DIR"
}

local_build() {
    require_root
    command -v mkarchiso >/dev/null 2>&1 || fail "mkarchiso not found. Install archiso."
    stage_installer
    clean_work
    info "Building the ISO with mkarchiso..."
    mkarchiso -v -w "$WORK_DIR" -o "$OUT_DIR" "$ROOT_DIR" \
        || fail "mkarchiso failed."
    ok "ISO written to out/$ISO_NAME"
}

container_build() {
    local runtime="${1:-}"
    command -v "$runtime" >/dev/null 2>&1 || return 1
    info "Running the build inside $runtime..."
    "$runtime" run --rm --privileged \
        -v "$ROOT_DIR:/build:z" \
        -w /build \
        archlinux/archlinux:latest \
        bash -c "pacman -Sy --noconfirm archiso python newt parted \
                 btrfs-progs xfsprogs dosfstools gptfdisk rsync git \
                 && bash /build/build.sh --isolated"
}

isolated_build() {
    require_root
    command -v mkarchiso >/dev/null 2>&1 || fail "mkarchiso not found (--isolated)."
    stage_installer
    clean_work
    mkarchiso -v -w "$WORK_DIR" -o "$OUT_DIR" "$ROOT_DIR" \
        || fail "mkarchiso failed."
    ok "ISO written to out/$ISO_NAME"
}

main() {
    case "${1:-}" in
        --local)    local_build ;;
        --isolated) isolated_build ;;
        *)
            container_build podman || container_build docker || local_build
            ;;
    esac
}

main "$@"