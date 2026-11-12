#!/bin/sh
# 打包成 TrollStore 可直装的 IPA。
#
# 重要：这里绝对不能在 CI 里做 codesign。
#
# 实测（TrollStore 的 trollstorehelper 日志）：
#   macOS runner 上 `codesign -s -` 给这个老式 cocos2d-x Mach-O 写出来的
#   签名结构是畸形的 —— SuperBlob 只有 1 个条目、且把 CodeDirectory 塞进
#   了 slot 0（magic 应为 0xfade0c01，实际是 0xfade0c02）。LaunchServices
#   解析时从错误偏移读到 SignatureVersion = 132352 (0x20500)，注册失败：
#       Error: Unable to register .../NarutoSenki.app
#       trollstorehelper returning 181
#
# 正确做法：把 LC_CODE_SIGNATURE 清成空槽位（dataoff 指向文件尾、
# datasize=0），签名完全交给 TrollStore 的 ldid 在设备上完成。
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

echo "----- 可执行文件 -----"
file "$BIN"
lipo -info "$BIN" || true

# 清掉可能来自构建机的扩展属性
xattr -cr "$APP_DIR" 2>/dev/null || true

echo "----- 清空代码签名（关键：不做本机签名） -----"
python3 ci/strip_sig.py "$BIN"

echo "----- 打包前校验 -----"
python3 ci/check_bundle.py "$APP_DIR"

zip -qry "$TARGET_NAME.ipa" Payload
ls -lh "$TARGET_NAME.ipa"
shasum -a 256 "$TARGET_NAME.ipa"
