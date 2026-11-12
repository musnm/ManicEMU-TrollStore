#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 app bundle 可被 TrollStore 注册的必备条件。

TrollStore 的流程：读 bundle → 用自带 ldid 重签 → LaunchServices 注册。
任何一项不满足都会返回 181 (ApplicationVerificationFailed)。

注意：我们刻意让可执行文件处于"未签名"状态（LC_CODE_SIGNATURE 空槽位），
由设备上的 ldid 填入签名。因此这里要求 datasize == 0。
若本机残留了 codesign 产物（残缺 SuperBlob），反而会导致
SignatureVersion 变成垃圾值 132352，注册失败。
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
        print("  [OK]   %s %s" % (name, detail))
    else:
        fail += 1
        print("  [FAIL] %s %s" % (name, detail))


plist_path = os.path.join(APP, "Info.plist")
check("Info.plist 存在", os.path.exists(plist_path))

info = plistlib.load(open(plist_path, "rb"))

# ---- 关键：#181 的直接诱因 ----
check("CFBundleSignature 已移除",
      "CFBundleSignature" not in info,
      repr(info.get("CFBundleSignature")))

exe = info.get("CFBundleExecutable", "")
check("CFBundleExecutable 非空", bool(exe), repr(exe))
check("无未展开变量",
      "${" not in exe and "${" not in str(info.get("CFBundleIdentifier", "")),
      exe)

bid = info.get("CFBundleIdentifier", "")
check("CFBundleIdentifier 合法",
      bool(bid) and "." in bid and " " not in bid, bid)
check("CFBundlePackageType=APPL",
      info.get("CFBundlePackageType") == "APPL",
      str(info.get("CFBundlePackageType")))
check("CFBundleVersion 存在", bool(info.get("CFBundleVersion")),
      str(info.get("CFBundleVersion")))
check("CFBundleShortVersionString 存在",
      bool(info.get("CFBundleShortVersionString")),
      str(info.get("CFBundleShortVersionString")))
check("MinimumOSVersion 存在", bool(info.get("MinimumOSVersion")),
      str(info.get("MinimumOSVersion")))

# ---- 图标 ----
icons = info.get("CFBundleIconFiles") or []
check("CFBundleIconFiles 非空", bool(icons), str(icons))
missing = [f for f in icons if not os.path.exists(os.path.join(APP, f))]
check("图标文件都存在", not missing, "缺: %s" % missing if missing else "")

# 图标必须是标准 PNG（CgBI 会导致桌面无图标）
cgbi = []
for f in icons:
    p = os.path.join(APP, f)
    if os.path.exists(p):
        head = open(p, "rb").read(24)
        if b"CgBI" in head:
            cgbi.append(f)
check("图标非 CgBI 格式", not cgbi, "CgBI: %s" % cgbi if cgbi else "")

bin_path = os.path.join(APP, exe)
check("可执行文件存在", os.path.exists(bin_path), bin_path)

if os.path.exists(bin_path):
    d = open(bin_path, "rb").read()
    magic = struct.unpack("<I", d[:4])[0]
    check("Mach-O 64 位", magic in (0xFEEDFACF, 0xCFFAEDFE), hex(magic))

    if magic == 0xFEEDFACF:
        ncmds = struct.unpack("<I", d[16:20])[0]
        off = 32
        sig = None
        have_buildver = False
        for _ in range(ncmds):
            cmd, sz = struct.unpack("<II", d[off:off + 8])
            if cmd == 0x1D:      # LC_CODE_SIGNATURE
                sig = struct.unpack("<II", d[off + 8:off + 16])
            if cmd == 0x32:      # LC_BUILD_VERSION
                have_buildver = True
            off += sz

        check("存在 LC_CODE_SIGNATURE 命令", sig is not None,
              "(ld 需用 -Wl,-adhoc_codesign 预留)")
        check("存在 LC_BUILD_VERSION", have_buildver)

        if sig is not None:
            dataoff, datasize = sig
            check("签名为空槽位（交给 ldid 签）", datasize == 0,
                  "dataoff=%d datasize=%d" % (dataoff, datasize))
            check("dataoff 不越界", dataoff <= len(d),
                  "dataoff=%d file=%d" % (dataoff, len(d)))

print("")
print("=" * 50)
if fail:
    print("校验失败 %d 项" % fail)
    sys.exit(1)
print("全部通过")
