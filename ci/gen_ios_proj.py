#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 cocos2d-x 2.2.6 官方 HelloCpp proj.ios 模板生成 NarutoSenki 的 iOS 工程。
"""
import os, re, sys, hashlib, shutil

SRC = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "src")
OUT = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else "out")

if not os.path.isdir(os.path.join(SRC, "cocos2dx")) \
        and os.path.isdir(os.path.join(SRC, "src/cocos2dx")):
    SRC = os.path.join(SRC, "src")
    print(f"[*] 自动切换源码根目录: {SRC}")

TPL_PROJ = os.path.join(SRC, "template/multi-platform-cpp/proj.ios")
GAME = os.path.join(SRC, "projects/NarutoSenki")
GAME_CLASSES = os.path.join(GAME, "Classes")
DST_PROJ = os.path.join(OUT, "projects/NarutoSenki/proj.ios")

TARGET_NAME = "NarutoSenki"
BUNDLE_ID = "com.leaderonepro.narutosenki"
DISPLAY_NAME = "火影战记"
VERSION = "1.22"
BUILD = "1"

SAMPLE_SOURCES = {"AppDelegate.cpp", "AppDelegate.h",
                  "HelloWorldScene.cpp", "HelloWorldScene.h"}
SAMPLE_RESOURCES = {"CloseNormal.png", "CloseSelected.png", "HelloWorld.png"}


def uid(seed):
    return hashlib.md5(seed.encode()).hexdigest().upper()[:24]


def collect(root):
    srcs, hdrs = [], []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for fn in sorted(filenames):
            ext = os.path.splitext(fn)[1].lower()
            rel = os.path.relpath(os.path.join(dirpath, fn), root).replace(os.sep, "/")
            if ext in (".cpp", ".cc", ".mm", ".m", ".c"):
                srcs.append(rel)
            elif ext in (".h", ".hpp"):
                hdrs.append(rel)
    return sorted(srcs), sorted(hdrs)


FILE_TYPE = {
    ".cpp": "sourcecode.cpp.cpp", ".cc": "sourcecode.cpp.cpp",
    ".mm": "sourcecode.cpp.objcpp", ".m": "sourcecode.c.objc",
    ".c": "sourcecode.c.c", ".h": "sourcecode.c.h", ".hpp": "sourcecode.c.h",
}


def ftype(name):
    return FILE_TYPE.get(os.path.splitext(name)[1].lower(), "text")


def _link_tree(src, dst, label):
    if os.path.islink(dst) or os.path.exists(dst):
        return
    r = os.system(f'cp -rl "{src}" "{dst}" >/dev/null 2>&1')
    if r == 0:
        print(f"[h] 硬链 {label}")
        return
    try:
        os.symlink(src, dst)
        print(f"[s] 软链 {label}")
        return
    except OSError:
        pass
    shutil.copytree(src, dst, symlinks=True)
    print(f"[c] 复制 {label}")


def mirror_tree():
    need = ["cocos2dx", "CocosDenshion", "extensions", "external",
            "scripting", "plugin", "tools", "samples", "template"]
    outs = os.path.join(OUT, "projects/NarutoSenki")
    os.makedirs(outs, exist_ok=True)
    for name in need:
        s = os.path.join(SRC, name)
        if os.path.isdir(s):
            _link_tree(s, os.path.join(OUT, name), name)
    for name in ("Classes", "Resources"):
        s = os.path.join(GAME, name)
        if os.path.isdir(s):
            _link_tree(s, os.path.join(outs, name), f"projects/NarutoSenki/{name}")


def insert_into_files_list(body, new_items):
    """把 new_items 插入到 `files = ( ... );` 列表内部，保持 OpenStep 结构合法。

    旧实现把新条目追加到 build phase 尾部（runOnlyForDeploymentPostprocessing
    之后），生成的项目文件结构损坏，xcodebuild 报：
    "The project ... is damaged and cannot be opened due to a parse error."
    """
    mf = re.search(r'(files = \()(.*?)(\s*\);)', body, re.S)
    assert mf, "找不到 files 列表"
    items = mf.group(2).rstrip()
    if items and not items.endswith(","):
        items += ","
    items += new_items
    return body[:mf.start(2)] + items + body[mf.end(2):]


def main():
    for d in (TPL_PROJ, GAME_CLASSES):
        assert os.path.isdir(d), f"目录不存在: {d}"

    mirror_tree()

    src = os.path.join(TPL_PROJ, "HelloCpp.xcodeproj/project.pbxproj")
    s = open(src, encoding="utf-8", errors="replace").read()

    srcs, hdrs = collect(GAME_CLASSES)
    print(f"[*] 源文件 {len(srcs)} 个 / 头文件 {len(hdrs)} 个")

    refs, builds, class_children, build_children = [], [], [], []

    for rel in hdrs + srcs:
        base = os.path.basename(rel)
        rid = uid("ref:" + rel)
        refs.append(
            f'\t\t{rid} /* {base} */ = {{isa = PBXFileReference; fileEncoding = 4; '
            f'lastKnownFileType = {ftype(base)}; name = "{base}"; '
            f'path = "{rel}"; sourceTree = "<group>"; }};'
        )
        class_children.append(f'\t\t\t\t{rid} /* {base} */,')
        if rel in srcs:
            bid = uid("build:" + rel)
            builds.append(
                f'\t\t{bid} /* {base} in Sources */ = {{isa = PBXBuildFile; '
                f'fileRef = {rid} /* {base} */; }};'
            )
            build_children.append(f'\t\t\t\t{bid} /* {base} in Sources */,')

    def drop_lines(text, names):
        dead_ids = set()
        out_lines = []
        for line in text.splitlines(True):
            if re.search(r'isa = PBX(FileReference|BuildFile)', line) and \
                    any(f'/* {n} */' in line for n in names):
                m = re.match(r'\t\t([0-9A-F]{24}) ', line)
                if m:
                    dead_ids.add(m.group(1))
                continue
            out_lines.append(line)
        return "".join(out_lines), dead_ids

    s, dead_sample = drop_lines(s, SAMPLE_SOURCES)
    s, more = drop_lines(s, SAMPLE_RESOURCES)
    dead_sample |= more

    for did in dead_sample:
        s = re.sub(rf'\n\t+{did} /\* [^*]+ \*/,(?=\n)', '', s)
        s = re.sub(rf'{did} /\* [^*]+ \*/, ', '', s)

    print(f"[*] 剔除样例对象 {len(dead_sample)} 个")

    m = re.search(r'([0-9A-F]{24}) /\* Classes \*/ = \{\s*isa = PBXGroup;(.*?)\};', s, re.S)
    assert m, "找不到 Classes group"
    old_classes_id = m.group(1)
    new_classes_id = uid("group:classes")
    new_group = (
        f'\t\t{new_classes_id} /* Classes */ = {{\n'
        '\t\t\tisa = PBXGroup;\n'
        '\t\t\tchildren = (\n' + "\n".join(class_children) + "\n"
        '\t\t\t);\n'
        '\t\t\tname = Classes;\n'
        '\t\t\tpath = ../Classes;\n'
        '\t\t\tsourceTree = "<group>";\n'
        '\t\t};'
    )
    s = re.sub(
        r'\n\t+[0-9A-F]{24} /\* Classes \*/ = \{\s*isa = PBXGroup;.*?\n\t+\};',
        '\n' + new_group, s, count=1, flags=re.S)
    s = s.replace(f'{old_classes_id} /* Classes */,', f'{new_classes_id} /* Classes */,')

    old_res_id = None
    m = re.search(r'([0-9A-F]{24}) /\* Resources \*/ = \{\s*isa = PBXGroup;(.*?)\};', s, re.S)
    if m:
        old_res_id = m.group(1)
        s = s[:m.start()] + s[m.end():]

    new_res_id = uid("ref:Resources.folder")
    res_ref = (
        f'\t\t{new_res_id} /* Resources */ = {{isa = PBXFileReference; '
        'lastKnownFileType = folder; name = Resources; path = ../Resources; '
        'sourceTree = "<group>"; };'
    )
    res_build_id = uid("build:Resources.folder")
    res_build = (
        f'\t\t{res_build_id} /* Resources in Resources */ = {{isa = PBXBuildFile; '
        f'fileRef = {new_res_id} /* Resources */; }};'
    )

    s = s.replace('/* End PBXFileReference section */',
                  res_ref + '\n/* End PBXFileReference section */', 1)
    s = s.replace('/* End PBXBuildFile section */',
                  res_build + '\n/* End PBXBuildFile section */', 1)

    if old_res_id:
        s = s.replace(f'{old_res_id} /* Resources */,', f'{new_res_id} /* Resources */,')
    else:
        s = re.sub(r'(\t+19C28FACFE9D520D11CA2CBB /\* Products \*/,\n)',
                   r'\1' + f'\t\t\t\t{new_res_id} /* Resources */,\n', s, count=1)

    m = re.search(r'([0-9A-F]{24}) /\* Resources \*/ = \{\s*isa = PBXResourcesBuildPhase;(.*?)\};', s, re.S)
    assert m, "找不到 Resources build phase"
    body = m.group(2)
    for did in dead_sample:
        body = re.sub(rf'\t+{did} /\* [^*]+ \*/,\n', '', body)
    body = insert_into_files_list(
        body, f'\n\t\t\t\t{res_build_id} /* Resources in Resources */,\n\t\t\t')
    s = s[:m.start(2)] + body + s[m.end(2):]

    m = re.search(r'([0-9A-F]{24}) /\* Sources \*/ = \{\s*isa = PBXSourcesBuildPhase;(.*?)\};', s, re.S)
    assert m, "找不到 Sources build phase"
    body = m.group(2)
    body = insert_into_files_list(
        body, "\n" + "\n".join(build_children) + "\n\t\t\t")
    s = s[:m.start(2)] + body + s[m.end(2):]

    s = s.replace('/* End PBXFileReference section */',
                  "\n".join(refs) + '\n/* End PBXFileReference section */', 1)
    s = s.replace('/* End PBXBuildFile section */',
                  "\n".join(builds) + '\n/* End PBXBuildFile section */', 1)

    s = s.replace('PRODUCT_NAME = HelloCpp;', f'PRODUCT_NAME = "{TARGET_NAME}";')
    s = s.replace('HelloCpp', TARGET_NAME)

    def ensure_setting(text, key, value):
        if re.search(rf'{key} = [^;]+;', text):
            return re.sub(rf'{key} = [^;]+;', f'{key} = {value};', text)
        return text.replace(
            f'PRODUCT_NAME = "{TARGET_NAME}";',
            f'PRODUCT_NAME = "{TARGET_NAME}";\n\t\t\t\t{key} = {value};')

    s = ensure_setting(s, "PRODUCT_BUNDLE_IDENTIFIER", f'"{BUNDLE_ID}"')
    s = ensure_setting(s, "MARKETING_VERSION", VERSION)
    s = ensure_setting(s, "CURRENT_PROJECT_VERSION", BUILD)
    s = ensure_setting(s, "IPHONEOS_DEPLOYMENT_TARGET", "12.0")
    s = ensure_setting(s, "ENABLE_BITCODE", "NO")
    s = ensure_setting(s, "CLANG_ENABLE_MODULES", "NO")

    s = re.sub(r'ARCHS = "[^"]*";', 'ARCHS = arm64;', s)
    s = re.sub(r'ARCHS = [^;]{0,60};', 'ARCHS = arm64;', s)
    s = re.sub(r'\n\t*VALID_ARCHS = [^;]+;', '', s)

    proj_dir = os.path.join(DST_PROJ, f"{TARGET_NAME}.xcodeproj")
    os.makedirs(proj_dir, exist_ok=True)
    open(os.path.join(proj_dir, "project.pbxproj"), "w", encoding="utf-8").write(s)
    print(f"[+] {proj_dir}/project.pbxproj  ({len(s)} bytes)")

    for fn in ["AppController.h", "AppController.mm", "RootViewController.h",
               "RootViewController.mm", "main.m", "Prefix.pch",
               "Icon-57.png", "Icon-114.png", "Icon-72.png", "Icon-144.png",
               "Icon-76.png", "Icon-120.png", "Icon-152.png",
               "Default.png", "Default@2x.png", "Default-568h@2x.png",
               "Default-667h@2x.png", "Default-736h@3x.png"]:
        sp = os.path.join(TPL_PROJ, fn)
        if os.path.exists(sp):
            shutil.copyfile(sp, os.path.join(DST_PROJ, fn))

    info_path = os.path.join(TPL_PROJ, "Info.plist")
    if os.path.exists(info_path):
        info = open(info_path, encoding="utf-8").read()
        info = info.replace("org.cocos2dx.hellocpp", BUNDLE_ID)
        info = info.replace("${PRODUCT_NAME}", DISPLAY_NAME)
        info = info.replace("<string></string>", f"<string>{VERSION}</string>", 1)
        info = info.replace("<key>CFBundleVersion</key>\n\t<string>1.0</string>",
                            f"<key>CFBundleVersion</key>\n\t<string>{BUILD}</string>")
        open(os.path.join(DST_PROJ, "Info.plist"), "w", encoding="utf-8").write(info)
        print(f"[+] {DST_PROJ}/Info.plist")
    print("[+] 完成")


if __name__ == "__main__":
    main()
