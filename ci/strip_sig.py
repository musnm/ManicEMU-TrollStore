#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 Mach-O 的 LC_CODE_SIGNATURE 置成"空槽位"（dataoff=0, datasize=0）。

背景（实测 TrollStore 日志）：
  macOS runner 的 `codesign -s -` 给这个老式 cocos2d-x 二进制写出的签名
  结构是畸形的：SuperBlob 只有 1 个条目，且把 CodeDirectory 塞进 slot 0，
  magic 也不对。LaunchServices 解析时从错误偏移读到
  SignatureVersion = 132352 (0x20500)，注册阶段直接失败：
      Error: Unable to register .../NarutoSenki.app
      trollstorehelper returning 181

  而完全不带 LC_CODE_SIGNATURE 的二进制，TrollStore 的 ldid 也无从下手。

所以这里保留 LC_CODE_SIGNATURE 命令本身（ld 已分配好），只把
dataoff/datasize 归零，文件截到签名数据之前。这样二进制处于干净的
"未签名但结构完整" 状态，设备和 ldid 都能正确处理。
"""
import os
import struct
import sys

LC_SEGMENT_64 = 0x19
LC_CODE_SIGNATURE = 0x1D
MH_MAGIC_64 = 0xFEEDFACF


def inspect(path):
    data = open(path, "rb").read()
    if struct.unpack("<I", data[:4])[0] != MH_MAGIC_64:
        return None
    ncmds = struct.unpack("<I", data[16:20])[0]
    off = 32
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack("<II", data[off:off + 8])
        if cmd == LC_CODE_SIGNATURE:
            dataoff, datasize = struct.unpack("<II", data[off + 8:off + 16])
            return off, dataoff, datasize, len(data)
        off += cmdsize
    return None


def classify(path):
    """判断二进制当前签名状态。"""
    info = inspect(path)
    if info is None:
        return "no-lc-sig-cmd"
    _, dataoff, datasize, filesize = info
    if datasize == 0:
        return "empty-slot"
    data = open(path, "rb").read()
    if dataoff + datasize > filesize:
        return "broken-outofrange"
    b = data[dataoff:dataoff + datasize]
    if struct.unpack(">I", b[:4])[0] != 0xFADE0CC0:
        return "broken-badmagic"
    count = struct.unpack(">I", b[8:12])[0]
    kinds = []
    for i in range(count):
        _, bo = struct.unpack(">II", b[12 + i * 8:20 + i * 8])
        kinds.append(hex(struct.unpack(">I", b[bo:bo + 4])[0]))
    if count == 1 and kinds and kinds[0] != "0xfade0c01":
        return "broken-slot0-%s" % kinds[0]
    return "signed-ok"


def clear_signature(path):
    """把 LC_CODE_SIGNATURE 置为零，并截断签名数据。"""
    with open(path, "rb") as f:
        data = bytearray(f.read())

    info = inspect(path)
    if info is None:
        print("  - 没有 LC_CODE_SIGNATURE 命令，保持原样")
        return True

    cmd_off, dataoff, datasize, filesize = info
    if datasize == 0 and dataoff == 0:
        print("  - 已经是空槽位")
        return True

    # 截断点：签名数据起点；若越界则用文件尾
    cut = dataoff if 0 < dataoff <= len(data) else len(data)

    # LC_CODE_SIGNATURE 置空。dataoff 用截断后的长度，datasize 为 0
    struct.pack_into("<II", data, cmd_off + 8, cut, 0)

    # __LINKEDIT 需同步收窄，否则 dyld 会按旧 filesize 越界映射
    ncmds = struct.unpack("<I", data[16:20])[0]
    off = 32
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack("<II", data[off:off + 8])
        if cmd == LC_SEGMENT_64:
            segname = bytes(data[off + 8:off + 24]).rstrip(b"\x00")
            if segname == b"__LINKEDIT":
                fileoff, fsize = struct.unpack("<QQ", data[off + 40:off + 56])
                if fileoff + fsize > cut:
                    struct.pack_into("<Q", data, off + 48, max(0, cut - fileoff))
                break
        off += cmdsize

    newdata = data[:cut]
    with open(path, "wb") as f:
        f.write(newdata)
    print("  -> 清空签名: %d -> %d bytes" % (filesize, len(newdata)))
    return True


def main():
    apps = sys.argv[1:]
    if not apps:
        print("用法: strip_sig.py <可执行文件...>")
        sys.exit(1)

    bad = 0
    for p in apps:
        print("[*] %s" % p)
        state = classify(p)
        print("  当前状态: %s" % state)
        if state == "no-lc-sig-cmd":
            # 链接时没加 -Wl,-adhoc_codesign，TrollStore 无法签名
            print("  [FAIL] 缺少 LC_CODE_SIGNATURE 命令，无法在设备上签名")
            bad += 1
            continue
        clear_signature(p)
        after = classify(p)
        print("  处理后: %s" % after)
        if after != "empty-slot":
            bad += 1

    print("")
    if bad:
        print("有 %d 个文件状态异常" % bad)
        sys.exit(1)
    print("全部为空的 LC_CODE_SIGNATURE 槽位，交给 TrollStore 签名")


if __name__ == "__main__":
    main()
