#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 gen_ios_proj.py 生成的 pbxproj 中的致命语法错误。幂等、不中断构建。"""
import os, re, sys

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
PROJ = os.path.join(ROOT, "out/projects/NarutoSenki/proj.ios")
PBX = os.path.join(PROJ, "NarutoSenki.xcodeproj/project.pbxproj")

if not os.path.exists(PBX):
    print("[!] missing " + PBX)
    sys.exit(1)

s = open(PBX, encoding="utf-8").read()
before = s

n1 = len(re.findall(r';,\s*\n', s))
s = re.sub(r';,\s*\n', ';\n', s)

n2 = len(re.findall(r'[{(]\s*,', s))
s = re.sub(r'([{(])\s*,', r'\1', s)

n3 = len(re.findall(r',\s*,', s))
s = re.sub(r',\s*,', ',', s)

print("[repair] semicolon-comma=%d brace-comma=%d double-comma=%d" % (n1, n2, n3))

PHASES = {
    "Sources": "PBXSourcesBuildPhase",
    "Resources": "PBXResourcesBuildPhase",
    "Frameworks": "PBXFrameworksBuildPhase",
    "CopyFiles": "PBXCopyFilesBuildPhase",
    "Headers": "PBXHeadersBuildPhase",
    "ShellScript": "PBXShellScriptBuildPhase",
}
fixed = 0
for name, isa in PHASES.items():
    pat = re.compile(
        r'(?P<id>[0-9A-F]{24}) /\* ' + name + r' \*/ = \{(?P<nl>\s*\n)'
        r'(?P<ind>\t+)(?P<nxt>exportPhases|buildActionMask|files|'
        r'runOnlyForDeploymentPostprocessing|name)')

    def rep(m, name=name, isa=isa):
        global fixed
        fixed += 1
        return (m.group('id') + ' /* ' + name + ' */ = {' + m.group('nl') +
                m.group('ind') + 'isa = ' + isa + ';\n' +
                m.group('ind') + m.group('nxt'))

    s = pat.sub(rep, s)
print("[repair] isa restored=%d" % fixed)

cnt = [0]


def fix_files(text):
    def rep(m):
        head, body, tail = m.group(1), m.group(2), m.group(3)
        out = []
        for ln in body.splitlines():
            t = ln.rstrip()
            if not t:
                continue
            if not t.endswith(','):
                t += ','
                cnt[0] += 1
            out.append(t)
        return head + "\n".join(out) + "\n" + tail

    return re.compile(r'(files = \(\n)(.*?)(\t+\);)', re.S).sub(rep, text)


s = fix_files(s)
print("[repair] files commas added=%d" % cnt[0])

if s != before:
    open(PBX, "w", encoding="utf-8").write(s)
    print("[+] wrote %d -> %d" % (len(before), len(s)))
else:
    print("[=] unchanged")

lb, rb = s.count("{"), s.count("}")
lp, rp = s.count("("), s.count(")")
if lb != rb or lp != rp:
    print("[!] unbalanced braces=%d/%d parens=%d/%d" % (lb, rb, lp, rp))
else:
    print("[ok] balanced")

try:
    import openstep_parser as osp
    d = osp.OpenStepDecoder.ParseFromString(s)
    print("[ok] openstep parse, objects=%d" % len(d['objects']))
except ImportError:
    print("[skip] openstep_parser unavailable")
except Exception as e:
    print("[!] openstep parse failed: " + type(e).__name__ + ": " + str(e))

print("[+] repair done")
sys.exit(0)
