#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Pack a MediaTek (MTK) Android boot image.

Stock GN3002 boot.img layout (verified against the 2017 factory image):
  * header v0, page_size 2048
  * kernel blob = Image.gz || DTB   (DTB starts right after the gzip stream)
  * header field at 0x28 (dt_size / header_version) == 0
  * cmdline in header = "bootopt=64S3,32N2,64N2"
  * LK appends the /chosen/bootargs from the DTB it was given

Usage:
  mkbootimg_mtk.py --kernel Image.gz --dtb gionee.dtb --ramdisk initrd.cpio.gz \
                   --cmdline "bootopt=64S3,32N2,64N2" --out boot.img [--separate-dtb]
"""
import argparse
import hashlib
import os
import struct

PAGE = 2048
KERNEL_ADDR = 0x40080000
RAMDISK_ADDR = 0x44000000
SECOND_ADDR = 0x40F00000
TAGS_ADDR = 0x4E000000


def pad(data, page=PAGE):
    rem = len(data) % page
    return data if rem == 0 else data + b'\x00' * (page - rem)


def build_header(kernel_size, ramdisk_size, second_size, dt_size, cmdline, name,
                 kernel=b'', ramdisk=b'', second=b''):
    hdr = bytearray()
    hdr += b'ANDROID!'
    hdr += struct.pack('<10I', kernel_size, KERNEL_ADDR, ramdisk_size,
                       RAMDISK_ADDR, second_size, SECOND_ADDR, TAGS_ADDR,
                       PAGE, dt_size, 0)
    hdr += name.encode()[:16].ljust(16, b'\x00')
    hdr += cmdline.encode()[:512].ljust(512, b'\x00')
    # id: sha1 over (data, size) of each section, as AOSP mkbootimg does
    sha = hashlib.sha1()
    for data in (kernel, ramdisk, second):
        sha.update(data)
        sha.update(struct.pack('<I', len(data)))
    hdr += sha.digest()
    hdr += b'\x00' * 12          # id field is 32 bytes: sha1 + zero padding
    hdr += b'\x00' * 1024        # extra_cmdline
    assert len(hdr) == 1632, len(hdr)
    return pad(bytes(hdr))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kernel', required=True, help='Image or Image.gz')
    ap.add_argument('--dtb')
    ap.add_argument('--ramdisk')
    ap.add_argument('--cmdline', default='bootopt=64S3,32N2,64N2')
    ap.add_argument('--name', default='')
    ap.add_argument('--out', required=True)
    ap.add_argument('--separate-dtb', action='store_true',
                    help='put DTB on its own page and set dt_size in the header '
                         '(mkbootimg style) instead of appending it to the kernel')
    args = ap.parse_args()

    kernel = open(args.kernel, 'rb').read()
    dtb = open(args.dtb, 'rb').read() if args.dtb else b''
    ramdisk = open(args.ramdisk, 'rb').read() if args.ramdisk else b''

    if args.dtb and not args.separate_dtb:
        kernel_blob = kernel + dtb
        dt_size = 0
    else:
        kernel_blob = kernel
        dt_size = len(dtb)

    out = bytearray()
    out += build_header(len(kernel_blob), len(ramdisk), 0, dt_size,
                        args.cmdline, args.name,
                        kernel=kernel_blob, ramdisk=ramdisk)
    out += pad(kernel_blob)
    if ramdisk:
        out += pad(ramdisk)
    if args.separate_dtb and dtb:
        out += pad(dtb)
    # images are padded to a multiple of the page size by the flash tool anyway

    with open(args.out, 'wb') as f:
        f.write(out)

    print('kernel blob : %d bytes (kernel %d + dtb %d)' %
          (len(kernel_blob), len(kernel), len(dtb) if not args.separate_dtb else 0))
    print('ramdisk     : %d bytes' % len(ramdisk))
    print('dt_size hdr : %d' % dt_size)
    print('image       : %d bytes -> %s' % (len(out), args.out))


if __name__ == '__main__':
    main()
