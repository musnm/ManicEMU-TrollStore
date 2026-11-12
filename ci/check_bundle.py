#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 app bundle 可被 TrollStore 注册的必备条件。

TrollStore 用 ldid 重签后又调用 LaunchServices 注册，任何一项不满足都会
返回 181 (ApplicationVerificationFailed)。
"""
import os
import plistlib
import struct
import sys

APP = os.path.abspath(sys.argv[1])
fail = 0


def check(name, cond, detail=""):
    global fail
    if cond:
        print(f"  [OK]   {name} {detail}")
    else:
        fail += 1
        print(f"  [FAIL] {name} {detail}")


plist_path = os.path.join(APP, "Info.plist")
check("Info.plist 存在", os.path.exists(plist_path))

info = plistlib.load(open(plist_path, "rb"))

exe = info.get("CFBundleExecutable", "")
check("CFBundleExecutable 非空", bool(exe), repr(exe))
check("没有未展开的变量", "${" not in exe and "${" not in info.get("CFBundleIdentifier", ""),
      exe)

bid = info.get("CFBundleIdentifier", "")
check("CFBundleIdentifier 合法", bool(bid) and "." in bid and " " not in bid, bid)
check("CFBundlePackageType=APPL", info.get("CFBundlePackageType") == "APPL",
      info.get("CFBundlePackageType"))
check("CFBundleVersion 存在", bool(info.get("CFBundleVersion")),
      info.get("CFBundleVersion"))
check("CFBundleShortVersionString 存在",
      bool(info.get("CFBundleShortVersionString")),
      info.get("CFBundleShortVersionString"))
check("MinimumOSVersion 存在", bool(info.get("MinimumOSVersion")),
      info.get("MinimumOSVersion"))

bin_path = os.path.join(APP, exe)
check("可执行文件存在", os.path.exists(bin_path), bin_path)

if os.path.exists(bin_path):
    d = open(bin_path, "rb").read()
    magic = struct.unpack("<I", d[:4])[0]
    check("Mach-O 64 位", magic in (0xFEEDFACF, 0xCFFAEDFE), hex(magic))

    ncmds = struct.unpack("<I", d[16:20])[0]
    off = 32
    have_sig = False
    have_buildver = False
    endian = "<" if magic == 0xFEEDFACF else ">"
    for _ in range(ncmds):
        cmd, sz = struct.unpack(endian + "II", d[off:off + 8])
        if cmd == 0x1D:          # LC_CODE_SIGNATURE
            have_sig = True
        if cmd == 0x32:          # LC_BUILD_VERSION
            have_buildver = True
        off += sz

    check("存在 LC_CODE_SIGNATURE", have_sig,
          "(TrollStore 依赖此段写入签名)")
    check("存在 LC_BUILD_VERSION", have_buildver)

    # arm64 需要 16KB 页对齐的代码签名
    if have_sig:
        off = 32
        for _ in range(ncmds):
            cmd, sz = struct.unpack(endian + "II", d[off:off + 8])
            if cmd == 0x1D:
                dataoff, datasize = struct.unpack(endian + "II", d[off + 8:off + 16])
                check("签名数据在文件内",
                      dataoff + datasize <= len(d),
                      f"off={dataoff} size={datasize} file={len(d)}")
                check("签名数据非空", datasize > 0, str(datasize))
                break
            off += sz

print("")
print("=" * 50)
if fail:
    print(f"校验失败 {fail} 项")
    sys.exit(1)
print("全部通过")
