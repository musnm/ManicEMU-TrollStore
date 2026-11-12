#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 Mach-O 的 LC_CODE_SIGNATURE 清成"空占位"。

背景：
  用 CODE_SIGNING_ALLOWED=NO + -Wl,-adhoc_codesign 编出来的二进制，
  签名段是一个 ad-hoc 签名。若在 CI 上再跑 codesign --sign -，
  在没有落盘签名身份的环境中会写出**残缺的 SuperBlob**：只有
  一个 slot，且 magic 是 0xfade0c02（entitlements）而不是
  0xfade0c01（CodeDirectory）。TrollStore 的 ldid 之后虽然能重签，
  但 LaunchServices 读到的 SignatureVersion 是垃圾值
  （132352 = 0x20500），注册阶段直接失败 → trollstorehelper returning 181。

正确做法：
  把 CodeDirectory 掏空——LC_CODE_SIGNATURE 的 dataoff 指向文件尾、
  datasize 置 0，文件截断到签名之前。这样二进制处于"未签名"状态，
  TrollStore 的 ldid 会自己分配空间写入完整签名。
"""
import os
import struct
import sys

LC_CODE_SIGNATURE = 0x1D


def strip_signature(path):
    with open(path, "rb") as f:
        data = bytearray(f.read())

    magic = struct.unpack("<I", data[:4])[0]
    if magic != 0xFEEDFACF:
        print("  [!] 不是 64 位 Mach-O (magic=%#x)，跳过" % magic)
        return False

    ncmds = struct.unpack("<I", data[16:20])[0]
    off = 32
    sig_cmd_off = None
    dataoff = datasize = 0

    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack("<II", data[off:off + 8])
        if cmd == LC_CODE_SIGNATURE:
            sig_cmd_off = off
            dataoff, datasize = struct.unpack("<II", data[off + 8:off + 16])
            break
        off += cmdsize

    if sig_cmd_off is None:
        print("  - 没有 LC_CODE_SIGNATURE，无需处理")
        return False

    print("  原签名: off=%d size=%d filesize=%d" % (dataoff, datasize, len(data)))

    if dataoff == 0 and datasize == 0:
        print("  - 已经是空占位")
        return False

    # 截断掉签名数据，并把 LC_CODE_SIGNATURE 置空
    new_len = min(dataoff, len(data)) if dataoff else len(data)
    struct.pack_into("<II", data, sig_cmd_off + 8, new_len, 0)
    data = data[:new_len]

    # __LINKEDIT 的 filesize/vmsize 需要同步缩小，否则 dyld 会越界
    fix_linkedit(data)

    with open(path, "wb") as f:
        f.write(data)

    print("  -> 已清空签名，新大小 %d" % len(data))
    return True


def fix_linkedit(data):
    """把 __LINKEDIT 段的 filesize 收回到实际内容末尾。"""
    ncmds = struct.unpack("<I", data[16:20])[0]
    off = 32
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack("<II", data[off:off + 8])
        if cmd == 0x19:  # LC_SEGMENT_64
            segname = bytes(data[off + 8:off + 24]).rstrip(b"\x00")
            if segname == b"__LINKEDIT":
                vmaddr, vmsize = struct.unpack("<QQ", data[off + 24:off + 40])
                fileoff, filesize = struct.unpack("<QQ", data[off + 40:off + 56])
                if fileoff + filesize > len(data):
                    struct.pack_into("<Q", data, off + 48, len(data) - fileoff)
                return
        off += cmdsize


def main():
    apps = sys.argv[1:]
    if not apps:
        print("用法: strip_sig.py <可执行文件...>")
        sys.exit(1)
    for p in apps:
        print("[*] %s" % p)
        strip_signature(p)


if __name__ == "__main__":
    main()
