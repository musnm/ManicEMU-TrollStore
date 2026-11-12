#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 app bundle 的 CFBundleIdentifier 换成新值。

为什么要这个：
  TrollStore 的 registerPath() (RootHelper/uicache.m:84) 在以下情况返回 false，
  调用方随即 return 181 (ApplicationVerificationFailed)：

    if([immutableAppBundleIdentifiers() containsObject:appBundleID.lowercaseString]) return false;

    immutableAppBundleIdentifiers() 收集的是"所有已安装、且 bundle 路径不在
    /private/var/containers 下"的 App 的 Bundle ID。也就是说，只要设备上曾经
    以任何方式（企业签/自签/AppSync）装过同一个 Bundle ID 的 App，这个 ID
    就进了黑名单，TrollStore 再也无法用它注册。

  另外 /System/Library/AppSignatures/<bundleID> 存在时会被判为
  isRemovableSystemApp，注册类型会变成 System，同样失败。

  换一个全新 Bundle ID 可以彻底绕开上述两条判定。
"""
import os
import plistlib
import sys


def main():
    app = os.path.abspath(sys.argv[1])
    newid = sys.argv[2]

    ip = os.path.join(app, "Info.plist")
    info = plistlib.load(open(ip, "rb"))
    old = info.get("CFBundleIdentifier")
    info["CFBundleIdentifier"] = newid
    plistlib.dump(info, open(ip, "wb"), fmt=plistlib.FMT_BINARY)
    print("  CFBundleIdentifier: %s -> %s" % (old, newid))

    if not old:
        return

    # 包内其他 plist 若也写了旧 ID，一并替换
    for root, dirs, files in os.walk(app):
        for fn in files:
            if not fn.endswith(".plist"):
                continue
            p = os.path.join(root, fn)
            if p == ip:
                continue
            try:
                d = plistlib.load(open(p, "rb"))
            except Exception:
                continue
            blob = repr(d)
            if old in blob:
                if isinstance(d, dict):
                    changed = False
                    for k, v in list(d.items()):
                        if isinstance(v, str) and v == old:
                            d[k] = newid
                            changed = True
                    if changed:
                        plistlib.dump(d, open(p, "wb"), fmt=plistlib.FMT_BINARY)
                        print("  [i] 已同步修改 %s" % os.path.relpath(p, app))
                else:
                    print("  [!] %s 含旧 ID（非 dict，未处理）" % os.path.relpath(p, app))


if __name__ == "__main__":
    main()
