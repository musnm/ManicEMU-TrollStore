#!/usr/bin/env python3
# 打包 ipa：只遍历 Payload，Mach-O 755，其他 644
# 用法: python3 pack.py <输出目录> [build目录] [输出文件名]
import os, sys, zipfile

MAGICS = {b'\xcf\xfa\xed\xfe', b'\xce\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca'}
FIXED_TIME = (1980, 1, 1, 0, 0, 0)

def is_macho(p):
    try:
        return open(p, 'rb').read(4) in MAGICS
    except Exception:
        return False

def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else '.'
    work = sys.argv[2] if len(sys.argv) > 2 else 'build'
    name = sys.argv[3] if len(sys.argv) > 3 else 'manicemu-trollstore.ipa'

    payload = os.path.join(work, 'Payload')
    if not os.path.isdir(payload):
        sys.exit('找不到 Payload: ' + payload)
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, name)

    if os.path.exists(out):
        os.remove(out)

    cnt = 0
    total = 0
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, dirs, files in os.walk(payload):
            dirs.sort()
            for d in sorted(dirs):
                p = os.path.join(root, d)
                zi = zipfile.ZipInfo(os.path.relpath(p, work).replace(os.sep, '/') + '/')
                zi.date_time = FIXED_TIME
                zi.external_attr = (0o40755 << 16) | 0x10
                zi.compress_type = zipfile.ZIP_STORED
                z.writestr(zi, b'')
            for f in sorted(files):
                p = os.path.join(root, f)
                mode = 0o100755 if is_macho(p) else 0o100644
                if mode == 0o100755:
                    cnt += 1
                zi = zipfile.ZipInfo(os.path.relpath(p, work).replace(os.sep, '/'))
                zi.date_time = FIXED_TIME
                zi.external_attr = mode << 16
                zi.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(zi, open(p, 'rb').read())
                total += 1

    size = os.path.getsize(out)
    print('打包完成 %s' % out)
    print('大小 %d 字节 (%.0f MB)，条目 %d，755 文件 %d 个' % (size, size/1048576, total, cnt))
    return 0

if __name__ == '__main__':
    sys.exit(main())
