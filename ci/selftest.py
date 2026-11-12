#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成后的工程完整性自检（含 openstep 语法与结构校验）。"""
import os, re, sys

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
if not os.path.isdir(os.path.join(ROOT, "out")) and \
        os.path.isdir(os.path.join(ROOT, "src/out")):
    ROOT = os.path.join(ROOT, "src")

PROJ = os.path.join(ROOT, "out/projects/NarutoSenki/proj.ios")
PBX = os.path.join(PROJ, "NarutoSenki.xcodeproj/project.pbxproj")

ok = fail = 0


def check(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  [OK]   {name} {detail}")
    else:
        fail += 1
        print(f"  [FAIL] {name} {detail}")


print("\n[1] 文件存在")
check("project.pbxproj", os.path.exists(PBX))
if not os.path.exists(PBX):
    sys.exit(1)

s = open(PBX, encoding="utf-8", errors="replace").read()

print("\n[2] OpenStep 语法解析")
tree = None
try:
    import openstep_parser as osp
    tree = osp.OpenStepDecoder.ParseFromString(s)
    check("openstep 解析", True, f"objects={len(tree['objects'])}")
except ImportError:
    print("  [SKIP] openstep_parser 未安装")
except Exception as e:
    check("openstep 解析", False, f"{type(e).__name__}: {e}")

print("\n[3] 结构完整性")
if tree:
    objs = tree["objects"]
    noisa = [k for k, v in objs.items() if not isinstance(v, dict) or "isa" not in v]
    check("所有对象都有 isa", not noisa, str(noisa[:3]))

    ids = re.findall(r'^\t\t([0-9A-Fa-f]{24}) ', s, re.M)
    dup = [k for k in set(ids) if ids.count(k) > 1]
    check("无重复 ID", not dup, str(dup[:3]))

    remote = set(re.findall(r'remoteGlobalIDString = ([0-9A-Fa-f]{24})', s))
    refs = set(re.findall(r'\b([0-9A-Fa-f]{24})\b', s))
    missing = refs - set(objs) - remote
    check("无悬空引用", not missing, str(sorted(missing)[:3]))

    for k, v in objs.items():
        if v.get("isa") == "PBXSourcesBuildPhase":
            check("Sources phase 有文件", len(v.get("files", [])) > 100,
                  f"{len(v.get('files', []))} 个")
        if v.get("isa") == "PBXResourcesBuildPhase":
            check("Resources phase 有文件", len(v.get("files", [])) > 0,
                  f"{len(v.get('files', []))} 个")

print("\n[4] 构建配置")
check("无 VALID_ARCHS", "VALID_ARCHS" not in s)
check("ARCHS=arm64", "ARCHS = arm64;" in s)
check("ENABLE_BITCODE=NO", "ENABLE_BITCODE = NO;" in s)
check("无 HelloCpp 残留", "HelloCpp" not in s)
check("PRODUCT_NAME", 'PRODUCT_NAME = "NarutoSenki";' in s)
m = re.search(r'PRODUCT_BUNDLE_IDENTIFIER = "([^"]+)";', s)
check("Bundle ID", bool(m), m.group(1) if m else "")
check("部署目标 >= 12", "IPHONEOS_DEPLOYMENT_TARGET = 12.0;" in s)
check("cocos2dx 子工程", "../../../cocos2dx/proj.ios/cocos2dx.xcodeproj" in s)
check("LIBRARY_SEARCH_PATHS 含产物目录", "CONFIGURATION_BUILD_DIR" in s)

print("\n[5] 游戏源文件")
for f in ["AppDelegate.cpp", "GameScene.cpp", "Characters.cpp",
          "ActionManager.cpp", "StartMenu.cpp", "NetworkLayer.cpp",
          "sqlite3.c", "KTools.cpp"]:
    check(f, f'/* {f} */' in s)

print("\n[6] 关键路径可达")
for p in ["../../../cocos2dx/proj.ios/cocos2dx.xcodeproj",
          "../../../cocos2dx/platform/third_party/ios/libraries/libcurl.a",
          "../../../external/Box2D", "../../../extensions",
          "../Classes/GameScene.cpp", "../Resources"]:
    check(p, os.path.exists(os.path.normpath(os.path.join(PROJ, p))))

print("\n" + "=" * 54)
print(f"通过 {ok} / 失败 {fail}")
sys.exit(1 if fail else 0)
