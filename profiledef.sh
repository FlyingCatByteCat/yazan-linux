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
  "/etc/shadow" "0:0:400"
  "/etc/gshadow" "0:0:400"
  "/etc/yazan/installer/main.py" "0:0:755"
  "/root" "0:0:750"
  "/root/.automated_script.sh" "0:0:755"
  "/etc/yazan/installer/assets/tux.txt" "0:0:644"
  "/etc/yazan/installer/assets/banner.txt" "0:0:644"
)