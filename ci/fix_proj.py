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

# 0) 工程格式：老模板是 objectVersion 46 / Xcode 3.2
s = re.sub(r'objectVersion = \d+;', 'objectVersion = 56;', s)
s = re.sub(r'compatibilityVersion = "[^"]*";',
           'compatibilityVersion = "Xcode 14.0";', s)
s = re.sub(r'LastUpgradeCheck = [0-9]+;', 'LastUpgradeCheck = 1600;', s)
if 'BuildIndependentTargetsInParallel' not in s:
    s = s.replace('LastUpgradeCheck = 1600;',
                  'LastUpgradeCheck = 1600;\n'
                  '\t\t\t\tBuildIndependentTargetsInParallel = YES;')
print("[+] objectVersion=56 compatibilityVersion=Xcode 14.0")

# 1) LIBRARY_SEARCH_PATHS 补产物目录（cocos2dx 静态库的来源）
LIB_PATHS = [
    '"$(inherited)"',
    '"$(SRCROOT)/../../../cocos2dx/platform/third_party/ios/libraries"',
    '"$(SRCROOT)/../../../external/libwebsockets/ios/lib"',
    '"$(SRCROOT)/libs"',
    '"$(CONFIGURATION_BUILD_DIR)"',
    '"$(BUILT_PRODUCTS_DIR)"',
]


def fix_lib_paths(text):
    pat = re.compile(r'(LIBRARY_SEARCH_PATHS = \(\n)((?:\s+"[^"]*",\n)+)(\s+\);)')

    def rep(m):
        indent = re.match(r'\s+', m.group(3)).group(0)
        body = "".join(indent + "\t" + p + ",\n" for p in LIB_PATHS)
        return m.group(1) + body + m.group(3)

    return pat.sub(rep, text)


s2 = fix_lib_paths(s)
print("[OK] LIBRARY_SEARCH_PATHS" if s2 != s else "[--] LIBRARY_SEARCH_PATHS")
s = s2

# 2) OTHER_LDFLAGS
#    HelloCpp 模板完全没有链接参数，app target 不会链接 libcocos2dx.a 和系统
#    框架，必然报 Undefined symbols（_cocos2d::*、_gl* 等）。
#    注意：不用 -all_load（与 -lcurl/-lwebp 组合会产生重复符号，
#    libcocos2dx.a 里的 Objective-C 分类由 -ObjC 负责加载）。
LDFLAGS = [
    "-lcocos2dx",
    "-lcurl", "-lwebp", "-lz", "-lsqlite3", "-lxml2",
    "-framework", "UIKit",
    "-framework", "Foundation",
    "-framework", "CoreGraphics",
    "-framework", "QuartzCore",
    "-framework", "OpenGLES",
    "-framework", "OpenAL",
    "-framework", "AVFoundation",
    "-framework", "AudioToolbox",
    "-framework", "CoreFoundation",
    "-framework", "Security",
    "-framework", "CoreMotion",
    "-framework", "MediaPlayer",
    "-ObjC",
]


def add_other_ldflags(text):
    if "OTHER_LDFLAGS" in text:
        return text

    def rep(m):
        indent = m.group(1)
        body = "".join(f'{indent}\t"{f}",\n' for f in LDFLAGS)
        return f'{indent}OTHER_LDFLAGS = (\n{body}{indent});\n' + m.group(0)

    return re.sub(r'([\t ]+)(?=LIBRARY_SEARCH_PATHS = \()', rep, text)


s3 = add_other_ldflags(s)
print("[+] OTHER_LDFLAGS" if s3 != s else "[--] OTHER_LDFLAGS")
s = s3

# 3) 架构
n = len(re.findall(r'\n\t+VALID_ARCHS = [^;]+;', s))
s = re.sub(r'\n\t+VALID_ARCHS = [^;]+;', '', s)
print("[+] 移除 VALID_ARCHS x%d" % n)

s = re.sub(r'IPHONEOS_DEPLOYMENT_TARGET = [^;]+;',
           'IPHONEOS_DEPLOYMENT_TARGET = 12.0;', s)
for v in ['"$(ARCHS_STANDARD_32_BIT)"', '"$(ARCHS_STANDARD)"',
          '"arm64 armv7 i386"']:
    s = s.replace('ARCHS = ' + v + ';', 'ARCHS = arm64;')

# 4) 签名与 bitcode
s = re.sub(r'CODE_SIGN_IDENTITY = "[^"]*";', 'CODE_SIGN_IDENTITY = "";', s)
s = re.sub(r'"CODE_SIGN_IDENTITY\[sdk=iphoneos\*\]" = "[^"]*";',
           '"CODE_SIGN_IDENTITY[sdk=iphoneos*]" = "";', s)
if 'ENABLE_BITCODE' in s:
    s = re.sub(r'ENABLE_BITCODE = [^;]+;', 'ENABLE_BITCODE = NO;', s)

open(PBX, "w", encoding="utf-8").write(s)
print("[+] 修补完成: %d -> %d bytes" % (orig_len, len(s)))
