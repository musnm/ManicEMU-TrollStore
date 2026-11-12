#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成后的工程结构自检。缺第三方库时降级，不因环境问题误报失败。"""
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
        print("  [OK]   " + name + " " + str(detail))
    else:
        fail += 1
        print("  [FAIL] " + name + " " + str(detail))


print("")
print("[1] 文件存在")
if not os.path.exists(PBX):
    print("  [FAIL] project.pbxproj 不存在: " + PBX)
    sys.exit(1)
check("project.pbxproj", True, "%d bytes" % os.path.getsize(PBX))

s = open(PBX, encoding="utf-8", errors="replace").read()

print("")
print("[2] 括号平衡")
check("花括号平衡", s.count("{") == s.count("}"),
      "%d/%d" % (s.count("{"), s.count("}")))
check("圆括号平衡", s.count("(") == s.count(")"),
      "%d/%d" % (s.count("("), s.count(")")))
check("无 ';,' 语法错", not re.search(r';,\s*\n', s))
check("无重复 ID", len(set(re.findall(r'^\t\t([0-9A-Fa-f]{24}) ', s, re.M))) ==
      len(re.findall(r'^\t\t([0-9A-Fa-f]{24}) ', s, re.M)))

print("")
print("[3] OpenStep 解析（可选）")
try:
    import openstep_parser as osp
    tree = osp.OpenStepDecoder.ParseFromString(s)
    objs = tree["objects"]
    print("  [OK]   openstep 解析 objects=%d" % len(objs))
    noisa = [k for k, v in objs.items()
             if not isinstance(v, dict) or "isa" not in v]
    check("所有对象都有 isa", not noisa, str(noisa[:3]))
    remote = set(re.findall(r'remoteGlobalIDString = ([0-9A-Fa-f]{24})', s))
    refs = set(re.findall(r'\b([0-9A-Fa-f]{24})\b', s))
    missing = refs - set(objs) - remote
    check("无悬空引用", not missing, str(sorted(missing)[:3]))
except ImportError:
    print("  [SKIP] openstep_parser 不可用，跳过深度校验")
except Exception as e:
    check("openstep 解析", False, type(e).__name__ + ": " + str(e))

print("")
print("[4] 构建配置")
check("无 VALID_ARCHS", "VALID_ARCHS" not in s)
check("ARCHS=arm64", "ARCHS = arm64;" in s)
check("ENABLE_BITCODE=NO", "ENABLE_BITCODE = NO;" in s)
check("无 HelloCpp 残留", "HelloCpp" not in s)
check("PRODUCT_NAME", 'PRODUCT_NAME = "NarutoSenki";' in s)
m = re.search(r'PRODUCT_BUNDLE_IDENTIFIER = "([^"]+)";', s)
check("Bundle ID", bool(m), m.group(1) if m else "")
check("部署目标 12.0", "IPHONEOS_DEPLOYMENT_TARGET = 12.0;" in s)
check("cocos2dx 子工程", "../../../cocos2dx/proj.ios/cocos2dx.xcodeproj" in s)

print("")
print("[5] 游戏源文件已加入 target")
for f in ["AppDelegate.cpp", "GameScene.cpp", "Characters.cpp",
          "ActionManager.cpp", "StartMenu.cpp", "NetworkLayer.cpp",
          "sqlite3.c", "KTools.cpp"]:
    check(f, ("/* " + f + " */") in s)

print("")
print("[6] 关键路径可达")
for p in ["../../../cocos2dx/proj.ios/cocos2dx.xcodeproj",
          "../../../cocos2dx/platform/third_party/ios/libraries/libcurl.a",
          "../../../external/Box2D", "../../../extensions",
          "../Classes/GameScene.cpp"]:
    check(p, os.path.exists(os.path.normpath(os.path.join(PROJ, p))))

print("")
print("=" * 54)
print("通过 %d / 失败 %d" % (ok, fail))
sys.exit(1 if fail else 0)
