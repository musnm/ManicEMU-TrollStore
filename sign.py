#!/usr/bin/env python3
# 批量重签：主程序带 entitlements，其余 Mach-O 空签，TrollStoreJITEnabler.dylib 跳过
# 用法: python3 sign.py <xxx.app 路径> [主程序名]
import os, subprocess, sys

MAGICS = {b'\xcf\xfa\xed\xfe', b'\xce\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca'}
SKIP_DYLIB = 'TrollStoreJITEnabler.dylib'

def is_macho(p):
    try:
        return open(p, 'rb').read(4) in MAGICS
    except Exception:
        return False

def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True)
    if r.returncode != 0:
        print('  警告 %s -> %s' % (cmd, r.stderr.decode('utf-8', 'ignore').strip()[:200]))
        return False
    return True

def main():
    APP = sys.argv[1].rstrip('/')
    if not os.path.isdir(APP):
        sys.exit('目录不存在: ' + APP)
    here = os.path.dirname(os.path.abspath(__file__))
    ENT = os.path.join(here, 'assets', 'ts.entitlements')

    if len(sys.argv) > 2:
        MAIN = os.path.join(APP, sys.argv[2])
    else:
        base = os.path.basename(APP)[:-4]
        MAIN = os.path.join(APP, base)
        if not os.path.isfile(MAIN):
            cands = [p for p in os.listdir(APP)
                     if os.path.isfile(os.path.join(APP, p))
                     and not os.path.splitext(p)[1] and is_macho(os.path.join(APP, p))]
            if not cands:
                sys.exit('找不到主程序，请手动指定第二个参数')
            MAIN = os.path.join(APP, cands[0])
    print('主程序: %s' % MAIN)

    if not os.path.isfile(ENT):
        sys.exit('缺 entitlements: ' + ENT)

    # 1. appex 主程序先签（空签）
    exe = 0
    for root, dirs, files in os.walk(APP):
        if 'PlugIns' not in root.split(os.sep):
            continue
        for f in files:
            p = os.path.join(root, f)
            if is_macho(p) and os.path.basename(p) != SKIP_DYLIB:
                sh('ldid -S "%s"' % p)
                exe += 1

    # 2. 其余 Mach-O 空签
    n = 0
    for root, _, files in os.walk(APP):
        for f in files:
            p = os.path.join(root, f)
            if os.path.abspath(p) == os.path.abspath(MAIN):
                continue
            if os.path.basename(p) == SKIP_DYLIB:
                continue
            if not is_macho(p):
                continue
            if sh('ldid -S "%s"' % p):
                n += 1
    print('空签 %d 个（含 appex %d 个）' % (n, exe))

    # 3. 主程序带权限签
    sh('ldid -S"%s" "%s"' % (ENT, MAIN))
    print('主程序已签名（ts.entitlements）')

    # 4. 校验 LC_CODE_SIGNATURE 末位
    import struct
    d = open(MAIN, 'rb').read()
    nm, sz = struct.unpack('<II', d[16:24])
    off = 32
    for _ in range(nm):
        c, s = struct.unpack('<II', d[off:off+8])
        if c == 0x1d:
            o, z = struct.unpack('<II', d[off+8:off+16])
            ok = (o + z == len(d))
            print('CODE_SIG %d+%d=%d  文件 %d  %s' % (o, z, o+z, len(d), 'OK' if ok else '不一致!'))
            return 0 if ok else 1
        off += s
    print('未找到 LC_CODE_SIGNATURE')
    return 1

if __name__ == '__main__':
    sys.exit(main())
