#!/usr/bin/env python3
# 在 .app 目录里定位主程序（Mach-O，优先与 .app 同名）
# 用法: python3 findmain.py <xxx.app>
import os, sys

MAG = {b'\xcf\xfa\xed\xfe', b'\xce\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca'}

def is_macho(p):
    try:
        return open(p, 'rb').read(4) in MAG
    except Exception:
        return False

def main():
    if len(sys.argv) < 2:
        sys.exit('用法: findmain.py <xxx.app>')
    app = sys.argv[1].rstrip('/')
    if not os.path.isdir(app):
        sys.exit('目录不存在: ' + app)

    base = os.path.basename(app)[:-4] if app.endswith('.app') else os.path.basename(app)
    cand = os.path.join(app, base)
    if os.path.isfile(cand) and is_macho(cand):
        print(cand)
        return 0

    for f in sorted(os.listdir(app)):
        p = os.path.join(app, f)
        if os.path.isfile(p) and not os.path.splitext(f)[1] and is_macho(p):
            print(p)
            return 0
    sys.exit('找不到主程序')

if __name__ == '__main__':
    sys.exit(main())
