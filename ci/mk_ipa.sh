#!/bin/sh
# 打包成 TrollStore 可直装的 IPA。
#
# 重要：这里绝对不能在 CI 里做 codesign。
#
# 实测（TrollStore 的 trollstorehelper 日志）：
#   macOS runner 上 `codesign -s -` 给这个老式 Mach-O 写出来的签名结构是
#   畸形的 —— SuperBlob 只有 1 个条目、且把 CodeDirectory 塞进了 slot 0
#   （magic 应为 0xfade0c01，实际是 0xfade0c02）。LaunchServices 解析时
#   从错误偏移读到 SignatureVersion = 132352，注册阶段直接失败：
#       Error: Unable to register .../NarutoSenki.app
#       trollstorehelper returning 181
#
# 正确做法：只让链接器预留一个空的 LC_CODE_SIGNATURE 槽位
# （-Wl,-adhoc_codesign 已在链接阶段完成），签名全部交给 TrollStore 的
# ldid 在设备上完成。
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

# 清掉构建机带来的扩展属性（否则会被打进 zip 的元数据里）
xattr -cr "$APP_DIR" 2>/dev/null || true

echo "----- 清除任何残留签名（关键） -----"
# ld 的 -adhoc_codesign 已给出 LC_CODE_SIGNATURE 槽位。这里若有 codesign
# 产物会被 TrollStore 误读，先去掉再重新留空槽。
codesign --remove-signature "$BIN" 2>/dev/null && echo "  已移除旧签名" || echo "  无旧签名"

echo "----- 打包前校验 -----"
python3 ci/check_bundle.py "$APP_DIR"

zip -qry "$TARGET_NAME.ipa" Payload
ls -lh "$TARGET_NAME.ipa"
shasum -a 256 "$TARGET_NAME.ipa"
