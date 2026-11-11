#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对源码打 iOS 适配补丁。"""
import os, sys

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")

if not os.path.isdir(os.path.join(ROOT, "projects/NarutoSenki/Classes")) \
        and os.path.isdir(os.path.join(ROOT, "src/projects/NarutoSenki/Classes")):
    ROOT = os.path.join(ROOT, "src")
    print(f"[*] 自动切换源码根目录: {ROOT}")

CLASSES = os.path.join(ROOT, "projects/NarutoSenki/Classes")
OUT_DIR = os.path.join(ROOT, "out")


def patch_appdelegate():
    p = os.path.join(CLASSES, "AppDelegate.cpp")
    if not os.path.exists(p):
        print(f"[!] 找不到 {p}")
        return
    s = open(p, encoding="utf-8", errors="replace").read()
    if "CC_PLATFORM_IOS" in s:
        print("[=] AppDelegate.cpp 已打过补丁")
        return
    marker = '#if (CC_TARGET_PLATFORM == CC_PLATFORM_MAC)'
    if marker in s:
        s = s.replace(
            marker,
            '#if (CC_TARGET_PLATFORM == CC_PLATFORM_MAC || CC_TARGET_PLATFORM == CC_PLATFORM_IOS)',
            1)
        open(p, "w", encoding="utf-8").write(s)
        print("[+] AppDelegate.cpp: MAC 条件扩展到 IOS")
    else:
        print("[!] 未找到 CC_PLATFORM_MAC 条件块")


def patch_info_plist():
    for cand in [
        os.path.join(ROOT, "projects/NarutoSenki/proj.ios/Info.plist"),
        os.path.join(OUT_DIR, "projects/NarutoSenki/proj.ios/Info.plist"),
    ]:
        if os.path.exists(cand):
            p = cand
            break
    else:
        print("[!] Info.plist 不存在，跳过")
        return
    s = open(p, encoding="utf-8").read()
    if "UIRequiresFullScreen" in s:
        print("[=] Info.plist 已有全屏配置")
        return
    s = s.replace(
        "<key>LSRequiresIPhoneOS</key>",
        "<key>UIRequiresFullScreen</key>\n\t<true/>\n"
        "\t<key>UIStatusBarHidden</key>\n\t<true/>\n"
        "\t<key>UIViewControllerBasedStatusBarAppearance</key>\n\t<false/>\n"
        "\t<key>LSRequiresIPhoneOS</key>", 1)
    open(p, "w", encoding="utf-8").write(s)
    print("[+] Info.plist 已补全屏/隐藏状态栏")


def write_export_options():
    p = os.path.join(OUT_DIR, "ExportOptions.plist")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
\t<key>method</key>
\t<string>development</string>
\t<key>signingStyle</key>
\t<string>automatic</string>
\t<key>compileBitcode</key>
\t<false/>
\t<key>stripSwiftSymbols</key>
\t<true/>
\t<key>thinning</key>
\t<string>&lt;none&gt;</string>
\t<key>destination</key>
\t<string>export</string>
</dict>
</plist>
""")
    print("[+] ExportOptions.plist")


if __name__ == "__main__":
    patch_appdelegate()
    patch_info_plist()
    write_export_options()
