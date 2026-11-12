#!/bin/sh
# 打包成 TrollStore 可直装的 IPA。
#
# 两条铁律：
#
# 1) 不在 CI 里做任何 codesign。
#    macOS runner 的 `codesign -s -` 给这个老式 cocos2d-x Mach-O 写出的签名
#    是残缺的 SuperBlob（只有 1 个 slot、magic 错成 0xfade0c02）。虽然
#    TrollStore 之后会用 ldid 重签，但干净起见这里只把 LC_CODE_SIGNATURE
#    清成空槽位，签名权完全交给设备上的 ldid。
#
# 2) CFBundleIdentifier 必须换新。
#    TrollStore 的 registerPath() 里：
#      if([immutableAppBundleIdentifiers() containsObject:appBundleID.lowercaseString])
#          return false;    // 调用方 return 181
#    immutableAppBundleIdentifiers() 收集"所有已安装、且路径不在
#    /private/var/containers 下"的 App 的 Bundle ID。只要设备上曾以别的方式
#    装过同一个 ID，该 ID 就进黑名单，TrollStore 永远注册不上。
#    另外 /System/Library/AppSignatures/<bundleID> 存在时会被判为
#    isRemovableSystemApp，注册类型变 System，同样失败。
#
#    实测设备上 com.leaderonepro.narutosenki 已有残留数据容器 CAC02D2A（绑定了
#    persona），三份日志里 ApplicationType 全是 System —— 正是命中了上述判定。
set -e

TARGET_NAME="${TARGET_NAME:-NarutoSenki}"
APP="$1"

if [ -z "$APP" ] || [ ! -d "$APP" ]; then
    echo "用法: mk.sh <App.app>"
    exit 1
fi

rm -rf Payload "$TARGET_NAME.ipa"
mkdir -p Payload
cp -R "$APP" "Payload/$TARGET_NAME.app"
APP_DIR="Payload/$TARGET_NAME.app"
BIN="$APP_DIR/$TARGET_NAME"

echo "----- CgBI PNG 转换 -----"
sh ci/fix_png.sh "$APP_DIR"

echo "----- Info.plist 修复 -----"
python3 ci/fix_infoplist.py "$APP_DIR"

echo "----- 更换 Bundle ID（绕开被占用的旧 ID） -----"
# 可用 NEW_BUNDLE_ID 覆盖
NEW_BUNDLE_ID="${NEW_BUNDLE_ID:-com.leaderonepro.narutosenki.ts}"
python3 ci/set_bundleid.py "$APP_DIR" "$NEW_BUNDLE_ID"

echo "----- 可执行文件 -----"
file "$BIN"
lipo -info "$BIN" || true

# 清掉可能来自构建机的扩展属性
xattr -cr "$APP_DIR" 2>/dev/null || true

echo "----- 清空代码签名槽位 -----"
python3 ci/strip_sig.py "$BIN"

echo "----- 打包前校验 -----"
python3 ci/check_bundle.py "$APP_DIR"

zip -qry "$TARGET_NAME.ipa" Payload
ls -lh "$TARGET_NAME.ipa"
shasum -a 256 "$TARGET_NAME.ipa"
