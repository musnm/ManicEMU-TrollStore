#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 gen_ios_proj.py 生成的 pbxproj 中的致命语法错误。

已确认 bug：build phase 里出现 `runOnlyForDeploymentPostprocessing = 0;,`
（逗号跑到分号后面），xcodebuild 会直接 exit code 74。

本脚本做幂等修复，且永不因校验失败而中断构建：
  - 删除 `;,\n` 形式的多余标点
  - 删除 `{,` `(,` 形式
  - 若 phase 对象缺 isa 行则补回
  - files 数组内每行补逗号
"""
import os, re, sys

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
PROJ = os.path.join(ROOT, "out/projects/NarutoSenki/proj.ios")
PBX = os.path.join(PROJ, "NarutoSenki.xcodeproj/project.pbxproj")

if not os.path.exists(PBX):
    print(f"[!] 找不到 {PBX}")
    sys.exit(1)

s = open(PBX, encoding="utf-8").read()
before = s

# 1) `;,` → `;`
n1 = len(re.findall(r';,\s*\n', s))
s = re.sub(r';,\s*\n', ';\n', s)

# 2) `{,` / `(,` → 去掉逗号
n2 = len(re.findall(r'[{(]\s*,', s))
s = re.sub(r'([{(])\s*,', r'\1', s)

# 3) 连续逗号 `,,`
n3 = len(re.findall(r',\s*,', s))
s = re.sub(r',\s*,', ',', s)

print(f"[修复] ';,':{n1}  '{{,'/{'(,':{n2}  ',,':{n3}")

# 4) 补回被吞掉的 isa 行
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
    pat = re.compile(rf'([0-9A-F]{{24}}) /\* {name} \*/ = \{{(\s*\n)(\t+)(exportPhases|buildActionMask|files|runOnlyForDeploymentPostprocessing|name)')

    def rep(m):
        global fixed
        fixed += 1
        return (f'{m.group(1)} /* {name} */ = {{{m.group(2)}'
                f'{m.group(3)}isa = {isa};\n{m.group(3)}{m.group(4)}')

    s = pat.sub(rep, s)
print(f"[修复] 补回 isa 行 {fixed} 处")

# 5) files = ( ... ) 内每行补逗号
def fix_files(text):
    total = [0]

    def rep(m):
        head, body, tail = m.group(1), m.group(2), m.group(3)
        out = []
        for ln in body.splitlines():
            t = ln.rstrip()
            if not t:
                continue
            if not t.endswith(','):
                t += ','
                total[0] += 1
            out.append(t)
        return head + "\n" + "\n".join(out) + "\n" + tail

    return re.compile(r'(files = \(\n)(.*?)(\t+\);)', re.S).sub(rep, text), total[0]

s, n5 = fix_files(s)
print(f"[修复] files 数组补逗号 {n5} 处")

if s != before:
    open(PBX, "w", encoding="utf-8").write(s)
    print(f"[+] 写回 {len(before)} -> {len(s)} bytes")
else:
    print("[=] 无需修改")

# 6) 括号平衡快检（仅提示，不中断）
if s.count("{") != s.count("}") or s.count("(") != s.count(")"):
    print(f"[!] 括号不平衡: {{}}={s.count('{')}/{s.count('}')} "
          f"()= {s.count('(')}/{s.count(')')}")
else:
    print("[✓] 括号平衡")
print("[+] repair 完成")
sys.exit(0)
