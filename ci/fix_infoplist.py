#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把构建产物的 Info.plist 修成 iOS / TrollStore 能正常注册的形态。

历史问题（会导致 trollstorehelper returning 181）：
  1. CFBundleSignature = "????"
     老 cocos2d-x 模板沿用了 Mac 的 Creator 字段，值写成四个问号。
     LaunchServices 会把它按 big-endian 读成整数 132352，与二进制里真正的
     签名信息对不上，注册阶段直接失败。
  2. CFBundleIconFiles 里列了 Icon.png / Icon@2x.png
     模板没有这两个文件，图标找不到 → 桌面无图标。
  3. 缺 CFBundleIcons / CFBundleIcons~ipad
     iOS 5+ 优先读这两个键，缺失时退回旧的 IconFiles，容易显示空白。
"""
import os
import plistlib
import struct
import sys


def png_size(path):
    d = open(path, "rb").read()
    i = d.find(b"IHDR")
    if i < 0:
        return None
    return struct.unpack(">II", d[i + 4:i + 12])


def main():
    app = os.path.abspath(sys.argv[1])
    plist_path = os.path.join(app, "Info.plist")
    info = plistlib.load(open(plist_path, "rb"))

    # ---- 1. CFBundleSignature ----
    old = info.get("CFBundleSignature")
    info["CFBundleSignature"] = "????" if not old else old
    # 直接删掉更安全：iOS 应用并不需要这个 Mac 时代的字段，
    # 留着反而会被 LaunchServices 当成签名版本号去比对。
    info.pop("CFBundleSignature", None)
    print("[1] CFBundleSignature: %r -> 移除" % (old,))

    # ---- 2. 收集真实存在的图标 ----
    exe = info.get("CFBundleExecutable", "")
    existing = {}
    for fn in os.listdir(app):
        if not (fn.lower().endswith(".png") and fn.startswith("Icon")):
            continue
        sz = png_size(os.path.join(app, fn))
        if sz:
            existing[fn] = sz
    print("[2] 实际图标: %s" % ", ".join("%s %dx%d" % (k, v[0], v[1])
                                         for k, v in sorted(existing.items())))

    if not existing:
        print("[!] 没有任何可用图标，跳过图标修复")
    else:
        # 按尺寸挑出 iOS 常用的几档
        by_size = {}
        for fn, sz in existing.items():
            by_size.setdefault(sz[0], fn)

        def pick(wanted):
            """挑最接近目标尺寸的图标文件名。"""
            if wanted in by_size:
                return by_size[wanted]
            best = min(by_size, key=lambda s: abs(s - wanted))
            return by_size[best]

        # 旧的 CFBundleIconFile 必须是真实存在的文件
        info["CFBundleIconFile"] = pick(57)
        # CFBundleIconFiles 只保留真实存在的
        info["CFBundleIconFiles"] = [
            fn for _, fn in sorted(by_size.items())
        ]

        # ---- 3. CFBundleIcons ----
        iphone_icons = [
            {"size": "29x29", "scale": "1x", "idiom": "iphone"},
            {"size": "29x29", "scale": "2x", "idiom": "iphone"},
            {"size": "40x40", "scale": "2x", "idiom": "iphone"},
            {"size": "60x60", "scale": "2x", "idiom": "iphone"},
            {"size": "60x60", "scale": "3x", "idiom": "iphone"},
        ]
        filled = []
        for entry in iphone_icons:
            w = int(entry["size"].split("x")[0])
            scale = 2 if entry["scale"] == "2x" else (3 if entry["scale"] == "3x" else 1)
            target = w * scale
            fn = pick(target)
            if fn:
                e = dict(entry)
                e["filename"] = fn
                filled.append(e)

        primary = pick(120)
        info["CFBundleIcons"] = {
            "CFBundlePrimaryIcon": {
                "CFBundleIconFiles": [primary],
                "CFBundleIconName": "AppIcon",
            },
            "CFBundleIconFiles": [primary],
        }
        if filled:
            info["CFBundleIcons"]["CFBundlePrimaryIcon"]["CFBundleIconFiles"] = \
                [e["filename"] for e in filled if e.get("filename")]
            # 去重并保序
            seen = set()
            uniq = []
            for fn in info["CFBundleIcons"]["CFBundlePrimaryIcon"]["CFBundleIconFiles"]:
                if fn not in seen:
                    seen.add(fn)
                    uniq.append(fn)
            info["CFBundleIcons"]["CFBundlePrimaryIcon"]["CFBundleIconFiles"] = uniq
        print("[3] CFBundleIcons -> %s" % info["CFBundleIcons"])

    # ---- 4. 其他注册相关字段 ----
    if not info.get("CFBundleName"):
        info["CFBundleName"] = info.get("CFBundleDisplayName", exe or "App")
    if not info.get("CFBundleVersion"):
        info["CFBundleVersion"] = "1"
    if not info.get("CFBundleShortVersionString"):
        info["CFBundleShortVersionString"] = info.get("CFBundleVersion", "1")
    info.setdefault("LSRequiresIPhoneOS", True)
    info.setdefault("UIDeviceFamily", [1, 2])
    info.setdefault("CFBundlePackageType", "APPL")

    # UIRequiredDeviceCapabilities 里的 arm64 在某些越狱环境会拦截安装
    caps = info.get("UIRequiredDeviceCapabilities")
    if isinstance(caps, list) and caps == ["arm64"]:
        info.pop("UIRequiredDeviceCapabilities", None)
        print("[4] 移除 UIRequiredDeviceCapabilities=[arm64]")

    plistlib.dump(info, open(plist_path, "wb"), fmt=plistlib.FMT_BINARY)
    print("[+] Info.plist 已重写: %s" % plist_path)

    # ---- 5. PkgInfo ----
    pk = os.path.join(app, "PkgInfo")
    with open(pk, "wb") as f:
        f.write(b"APPL????")
    print("[5] PkgInfo -> APPL????")


if __name__ == "__main__":
    main()
