#!/usr/bin/env bash
set -e -u

# Yazan Linux -- archiso profile definition.
# Internal comments reference vanilla Arch tooling (mkarchiso).

iso_name="yazan-linux"
iso_label="YAZAN_$(date +%Y%m)"
iso_publisher="Yazan Linux <https://yazanlinux.org>"
iso_application="Yazan Linux Live/Rescue ISO"
iso_version="1.0.0"
install_dir="arch"
buildmodes=('iso')
bootmodes=('bios.syslinux'
           'uefi.systemd-boot')
arch="x86_64"
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'xz' '-Xbcj' 'x86' '-b' '1M')
file_permissions=(
  "/etc/yazan/installer/main.py" "0:0:755"
)