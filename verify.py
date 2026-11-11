#!/usr/bin/env python3
# 产物自检，不符合手册步骤 10 就退出 1
# 用法: python3 verify.py <ipa路径> [是否要求含dylib 1/0]
import sys, zipfile

def main():
    path = sys.argv[1]
    need_dylib = (len(sys.argv) < 3) or (sys.argv[2] != '0')
    z = zipfile.ZipFile(path)
    n = z.namelist()
    top = sorted({p.split('/')[0] for p in n})
    ipa = [p for p in n if p.endswith('.ipa')]
    prov = [p for p in n if 'mobileprovision' in p]
    crc = z.testzip()
    dyl = [p for p in n if p.endswith('TrollStoreJITEnabler.dylib')]
    dsz = z.getinfo(dyl[0]).file_size if dyl else 0

    print('顶层       ', top)
    print('嵌套 ipa   ', ipa or '无')
    print('provision  ', prov or '无')
    print('CRC        ', crc or '全通')
    print('dylib      ', dsz if dyl else '缺失')

    bad = []
    if top != ['Payload']:
        bad.append('顶层不是只有 Payload')
    if ipa:
        bad.append('含嵌套 ipa')
    if prov:
        bad.append('含 provision')
    if crc:
        bad.append('CRC 错误: ' + crc)
    if need_dylib and dsz != 158896:
        bad.append('dylib 大小 %s != 158896' % dsz)

    if bad:
        print('::error::' + '; '.join(bad))
        return 1
    print('自检通过')
    return 0

if __name__ == '__main__':
    sys.exit(main())
