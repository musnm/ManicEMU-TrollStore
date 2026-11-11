#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成后的工程完整性自检。"""
import os, re, sys, plistlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "out")
PROJ = os.path.join(OUT, "projects/NarutoSenki/proj.ios")
PBX = os.path.join(PROJ, "NarutoSenki.xcodeproj/project.pbxproj")

ok, fail = 0, 0


def check(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  [OK] {name} {detail}")
    else:
        fail += 1
        print(f"  [FAIL] {name} {detail}")


print("\n[1] pbxproj 完整性")
check("project.pbxproj 存在", os.path.exists(PBX))
if not os.path.exists(PBX):
    print("\n生成失败，终止")
    sys.exit(1)

s = open(PBX, encoding="utf-8", errors="replace").read()
check("花括号平衡", s.count("{") == s.count("}"))
check("圆括号平衡", s.count("(") == s.count(")"))
defined = set(re.findall(r'^\t\t([0-9A-Fa-f]{24}) /\*', s, re.M))
refs = set(re.findall(r'([0-9A-Fa-f]{24}) /\*', s)) \
     | set(re.findall(r'fileRef = ([0-9A-Fa-f]{24})', s))
missing = refs - defined
check("无悬空引用", not missing, str(sorted(missing)[:3]))
check("无 VALID_ARCHS", "VALID_ARCHS" not in s)
check("ARCHS=arm64", "ARCHS = arm64;" in s)
check("ENABLE_BITCODE=NO", "ENABLE_BITCODE = NO;" in s)
check("无 HelloCpp 残留", "HelloCpp" not in s and "HelloWorldScene" not in s)

print("\n[2] 目标配置")
check("PRODUCT_NAME", 'PRODUCT_NAME = "NarutoSenki";' in s)
m = re.search(r'PRODUCT_BUNDLE_IDENTIFIER = "([^"]+)";', s)
check("Bundle ID", bool(m), m.group(1) if m else "")
check("cocos2dx 子工程", "../../../cocos2dx/proj.ios/cocos2dx.xcodeproj" in s)
check("部署目标", "IPHONEOS_DEPLOYMENT_TARGET = 12.0;" in s)

print("\n[3] 游戏源文件在 target 里")
for f in ["AppDelegate.cpp", "GameScene.cpp", "Characters.cpp",
          "ActionManager.cpp", "StartMenu.cpp", "NetworkLayer.cpp",
          "sqlite3.c", "CCShake.cpp", "KTools.cpp"]:
    check(f, f'/* {f} */' in s)

print("\n[4] Resources")
res = os.path.join(OUT, "projects/NarutoSenki/Resources")
check("Resources 目录存在", os.path.isdir(res))
check("folder reference", "lastKnownFileType = folder" in s)

print("\n[5] Info.plist")
ipl = os.path.join(PROJ, "Info.plist")
check("Info.plist 存在", os.path.exists(ipl))
if os.path.exists(ipl):
    d = plistlib.load(open(ipl, "rb"))
    check("Bundle ID", d.get("CFBundleIdentifier") == "com.leaderonepro.narutosenki")
    check("横屏", d.get("UISupportedInterfaceOrientations") ==
          ["UIInterfaceOrientationLandscapeLeft", "UIInterfaceOrientationLandscapeRight"])

print("\n[6] 关键路径可达")
for p in ["../../../cocos2dx/proj.ios/cocos2dx.xcodeproj",
          "../../../cocos2dx/platform/third_party/ios/libraries/libcurl.a",
          "../../../cocos2dx/platform/third_party/ios/libraries/libwebp.a",
          "../../../external/Box2D", "../../../extensions",
          "../Classes/GameScene.cpp", "../Resources"]:
    check(p, os.path.exists(os.path.normpath(os.path.join(PROJ, p))))

print("\n" + "=" * 52)
print(f"通过 {ok} / 失败 {fail}")
sys.exit(1 if fail else 0)
