#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
# bring-up 阶段裁剪内核配置：
# 砍掉与「串口 + USB gadget + pstore + eMMC」首启无关的子系统，
# 加快编译、缩小 Image。设备点亮后按需逐项加回。
set -e
KDIR="${1:?usage: trim-config.sh <kernel-dir>}"
cd "$KDIR"

./scripts/config \
  --disable DEBUG_INFO \
  --disable DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT \
  --disable SND \
  --disable DRM \
  --disable MEDIA_SUPPORT \
  --disable WLAN \
  --disable CFG80211 \
  --disable MAC80211 \
  --disable BT \
  --disable NFC \
  --disable SCSI \
  --disable BLK_DEV_SD \
  --disable ATA \
  --disable USB_STORAGE \
  --disable HID \
  --disable USB_HID \
  --disable INPUT_MOUSE \
  --disable INPUT_UINPUT \
  --disable NETFILTER \
  --disable NET_SCHED \
  --disable NET_CLS \
  --disable NET_ACT \
  --disable IPV6 \
  --disable NET_IP_TUNNEL \
  --disable INET_TUNNEL \
  --disable INET_DIAG \
  --disable TUN \
  --disable VXLAN \
  --disable XEN \
  --disable F2FS_FS \
  --disable NTFS_FS \
  --disable NTFS3_FS \
  --disable UDF_FS \
  --disable XFS_FS \
  --disable BTRFS_FS \
  --disable JFS_FS \
  --disable GFS2_FS \
  --disable BEFS_FS \
  --disable DLM \
  --disable PERF_EVENTS \
  --disable FTRACE \
  --disable KPROBES \
  --disable AUDIT \
  --disable AUDITSYSCALL \
  --disable SECURITY \
  --disable IMA \
  --disable EVM \
  --disable SWAP \
  --disable CPU_FREQ \
  --disable HIBERNATION

echo "config trimmed for bring-up"
