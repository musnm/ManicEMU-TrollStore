#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_ios_proj.py 之后的工程修补。"""
import os, re, sys

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
if not os.path.isdir(os.path.join(ROOT, "out")) and \
        os.path.isdir(os.path.join(ROOT, "src/out")):
    ROOT = os.path.join(ROOT, "src")

PBX = os.path.join(
    ROOT, "out/projects/NarutoSenki/proj.ios/NarutoSenki.xcodeproj/project.pbxproj")

if not os.path.exists(PBX):
    print("[!] 找不到 " + PBX)
    sys.exit(1)

s = open(PBX, encoding="utf-8").read()
orig_len = len(s)

# 0) 工程格式升级：objectVersion 46 / Xcode 3.2 在老模板里，Xcode 16 会报
#    "the project is damaged and cannot be opened due to a parse error"
s = re.sub(r'objectVersion = \d+;', 'objectVersion = 56;', s)
s = re.sub(r'compatibilityVersion = "[^"]*";',
           'compatibilityVersion = "Xcode 14.0";', s)
s = re.sub(r'LastUpgradeCheck = [0-9]+;', 'LastUpgradeCheck = 1600;', s)
if 'BuildIndependentTargetsInParallel' not in s:
    s = s.replace('LastUpgradeCheck = 1600;',
                  'LastUpgradeCheck = 1600;\n'
                  '\t\t\t\tBuildIndependentTargetsInParallel = YES;')
print("[+] objectVersion=56 compatibilityVersion=Xcode 14.0")

# 1) LIBRARY_SEARCH_PATHS 补产物目录
def fix_lib_paths(text):
    pat = re.compile(r'(LIBRARY_SEARCH_PATHS = \(\n)((?:\s+"[^"]*",\n)+)(\s+\);)')

    def rep(m):
        indent = re.match(r'\s+', m.group(3)).group(0)
        paths = [
            '"$(inherited)"',
            '"$(SRCROOT)/../../../cocos2dx/platform/third_party/ios/libraries"',
            '"$(SRCROOT)/../../../external/libwebsockets/ios/lib"',
            '"$(CONFIGURATION_BUILD_DIR)"',
            '"$(BUILT_PRODUCTS_DIR)"',
        ]
        body = "".join(indent + "\t" + p + ",\n" for p in paths)
        return m.group(1) + body + m.group(3)

    return pat.sub(rep, text)


s2 = fix_lib_paths(s)
print("[OK] LIBRARY_SEARCH_PATHS" if s2 != s else "[--] LIBRARY_SEARCH_PATHS")
s = s2

# 2) 架构
n = len(re.findall(r'\n\t+VALID_ARCHS = [^;]+;', s))
s = re.sub(r'\n\t+VALID_ARCHS = [^;]+;', '', s)
print("[+] 移除 VALID_ARCHS x%d" % n)

s = re.sub(r'IPHONEOS_DEPLOYMENT_TARGET = [^;]+;',
           'IPHONEOS_DEPLOYMENT_TARGET = 12.0;', s)
for v in ['"$(ARCHS_STANDARD_32_BIT)"', '"$(ARCHS_STANDARD)"',
          '"arm64 armv7 i386"']:
    s = s.replace('ARCHS = ' + v + ';', 'ARCHS = arm64;')

# 3) 签名与 bitcode
s = re.sub(r'CODE_SIGN_IDENTITY = "[^"]*";', 'CODE_SIGN_IDENTITY = "";', s)
s = re.sub(r'"CODE_SIGN_IDENTITY\[sdk=iphoneos\*\]" = "[^"]*";',
           '"CODE_SIGN_IDENTITY[sdk=iphoneos*]" = "";', s)
if 'ENABLE_BITCODE' in s:
    s = re.sub(r'ENABLE_BITCODE = [^;]+;', 'ENABLE_BITCODE = NO;', s)

open(PBX, "w", encoding="utf-8").write(s)
print("[+] 修补完成: %d -> %d bytes" % (orig_len, len(s)))
