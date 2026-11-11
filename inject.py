#!/usr/bin/env python3
# 往 Mach-O 头里注入 LC_LOAD_WEAK_DYLIB
# 用法: python3 inject.py <主程序路径> [dylib文件名]
import struct, sys

WEAK = 0x80000018
LC_SEGMENT_64 = 0x19

def fat_check(b):
    if b[:4] in (b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca'):
        sys.exit('这是 fat 二进制，只对 thin 主程序操作')
    if b[:4] == b'\xcf\xfa\xed\xfe':
        return 'macho64'
    sys.exit('未知格式: %s' % b[:4].hex())

def main():
    path = sys.argv[1]
    dylib = sys.argv[2] if len(sys.argv) > 2 else 'TrollStoreJITEnabler.dylib'
    b = bytearray(open(path, 'rb').read())
    fat_check(b)

    ncmds, sz = struct.unpack('<II', b[16:24])
    off = 32
    first_data = 1 << 62
    for _ in range(ncmds):
        cmd, csz = struct.unpack('<II', b[off:off+8])
        if cmd == WEAK:
            no = struct.unpack('<I', b[off+8:off+12])[0]
            if b'TrollStore' in bytes(b[off+no:off+csz]):
                print('已有加载命令，跳过')
                return 0
        if cmd == LC_SEGMENT_64:
            name = bytes(b[off+8:off+24]).rstrip(b'\0').decode('utf-8', 'ignore')
            nsects = struct.unpack('<I', b[off+64:off+68])[0]
            if name != '__PAGEZERO' and nsects:
                so = off + 72
                for i in range(nsects):
                    s_off = struct.unpack('<I', b[so+i*80+48:so+i*80+52])[0]
                    s_size = struct.unpack('<Q', b[so+i*80+40:so+i*80+48])[0]
                    if s_size and s_off:
                        first_data = min(first_data, s_off)
        off += csz

    nm = ('@executable_path/' + dylib).encode() + b'\0'
    raw = bytearray(struct.pack('<IIIIII', WEAK, 0, 24, 0, 0, 0x10000) + nm)
    raw += b'\0' * ((8 - len(raw) % 8) % 8)
    ins = 32 + sz
    gap = first_data - ins
    print('ncmds %d  sizeofcmds %d  空隙 %d  需要 %d' % (ncmds, sz, gap, len(raw)))
    if ins + len(raw) > first_data:
        print('头部空隙不足：需要 %d，只有 %d' % (len(raw), gap))
        print('这条二进制没有 padding，需要插入式注入，停止')
        return 1
    struct.pack_into('<II', raw, 0, WEAK, len(raw))
    b[ins:ins+len(raw)] = raw
    struct.pack_into('<II', b, 16, ncmds+1, sz+len(raw))
    open(path, 'wb').write(b)
    print('注入完成：ncmds %d->%d, sizeofcmds %d->%d' % (ncmds, ncmds+1, sz, sz+len(raw)))
    return 0

if __name__ == '__main__':
    sys.exit(main())
