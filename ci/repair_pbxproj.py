#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立修复 gen_ios_proj.py 生成的 pbxproj 中的致命语法错误。

已确认的两个 bug（在 CI 上由 openstep_parser 报出）：
  1. build phase 里 `runOnlyForDeploymentPostprocessing = 0;,` —— 逗号出现在分号后面
  2. 少数 phase 的 `isa = PBXxxxBuildPhase;` 行被吞掉

本脚本对生成的 project.pbxproj 做幂等修复：
  - 删除 `;,\n` 形式的多余标点
  - 若某个 phase 对象缺少 isa 行，按名称补回
  - 保证 files = (...) 数组内每项以逗号结尾
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

# ---------- 修复 1：`;,` 这类非法标点 ----------
n1 = len(re.findall(r';,\s*\n', s))
s = re.sub(r';,\s*\n', ';\n', s)
print(f"[1] 修掉 ';,' 共 {n1} 处")

# ---------- 修复 2：`{,` 或 `{ ;` 之类 ----------
n2 = len(re.findall(r'\{\s*,', s))
s = re.sub(r'\{\s*,', '{', s)
print(f"[2] 修掉 '{,' 共 {n2} 处")

# ---------- 修复 3：补回被吞掉的 isa 行 ----------
PHASES = ["PBXSourcesBuildPhase", "PBXResourcesBuildPhase",
          "PBXFrameworksBuildPhase", "PBXCopyFilesBuildPhase",
          "PBXHeadersBuildPhase", "PBXShellScriptBuildPhase"]
fixed_isa = 0
for isa in PHASES:
    name = isa[3:-len("BuildPhase")]      # Sources / Resources / Frameworks ...
    # 找 `<id> /* Sources */ = {` 后面第一行不是 isa 的情况
    pat = re.compile(
        rf'([0-9A-F]{{24}}) /\* {name} \*/ = \{{(\s*\n)\t+([a-zA-Z])')
    def rep(m):
        global fixed_isa
        nxt = m.group(3)
        if nxt == 'i':
            return m.group(0)
        fixed_isa += 1
        return (f'{m.group(1)} /* {name} */ = {{{m.group(2)}'
                f'\t\t\tisa = {isa};\n\t\t\t{nxt}')
    s = pat.sub(rep, s)
print(f"[3] 补回缺失的 isa 行 {fixed_isa} 处")

# ---------- 修复 4：files 数组内每行补逗号 ----------
def fix_files_arrays(text):
    total = 0

    def rep(m):
        nonlocal total
        head, body, tail = m.group(1), m.group(2), m.group(3)
        lines = []
        for ln in body.splitlines():
            t = ln.rstrip()
            if not t:
                continue
            if not t.endswith(','):
                t += ','
                total += 1
            lines.append(t)
        return head + "\n" + "\n".join(lines) + "\n" + tail

    pat = re.compile(r'(files = \(\n)(.*?)(\t+\);)', re.S)
    return pat.sub(rep, text), total

s, n4 = fix_files_arrays(s)
print(f"[4] files 数组补逗号 {n4} 处")

if s != before:
    open(PBX, "w", encoding="utf-8").write(s)
    print(f"[+] 已写回 ({len(before)} -> {len(s)} bytes)")
else:
    print("[=] 无需修改")

# ---------- 校验 ----------
try:
    import openstep_parser as osp
    d = osp.OpenStepDecoder.ParseFromString(s)
    print(f"[✓] OpenStep 解析通过，objects = {len(d['objects'])}")
except ImportError:
    print("[!] openstep_parser 未安装，跳过校验")
except Exception as e:
    print(f"[✗] 仍解析失败: {type(e).__name__}: {e}")
    sys.exit(1)
