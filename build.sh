#!/bin/sh
# ManicEMU SideloadJIT -> TrollStore 一键转制
# 用法: sh build.sh <SideloadJIT的ipa> [输出目录]
set -e

IPA="$1"
OUTDIR="${2:-.}"
[ -z "$IPA" ] && { echo "用法: sh build.sh <SideloadJIT的ipa> [输出目录]"; exit 1; }
[ -f "$IPA" ] || { echo "文件不存在: $IPA"; exit 1; }

HERE=$(cd "$(dirname "$0")" && pwd)
ASSETS="$HERE/assets"
WORK="$HERE/build"

for f in "$ASSETS/TrollStoreJITEnabler.dylib" "$ASSETS/ts.entitlements"; do
  [ -f "$f" ] || { echo "缺素材: $f"; exit 1; }
done

echo "[1/6] 清理旧 build"
if [ -d "$WORK" ]; then
  find "$WORK" -type f -delete 2>/dev/null || true
  find "$WORK" -depth -type d -exec rmdir {} \; 2>/dev/null || true
fi
mkdir -p "$WORK"

echo "[2/6] 解包"
unzip -q -o "$IPA" -d "$WORK" 2>/dev/null || true
APP=$(find "$WORK/Payload" -maxdepth 1 -name "*.app" | head -1)
[ -z "$APP" ] && { echo "解包后找不到 .app"; exit 1; }
echo "  app: $APP"

echo "[3/6] 放入 dylib（cat 不用 cp）"
cat "$ASSETS/TrollStoreJITEnabler.dylib" > "$APP/TrollStoreJITEnabler.dylib"
SZ=$(wc -c < "$APP/TrollStoreJITEnabler.dylib")
[ "$SZ" -eq 158896 ] || { echo "  dylib 大小异常: $SZ"; exit 1; }
echo "  $SZ 字节 OK"

echo "[4/6] 注入加载指令"
MAIN=$(python3 "$HERE/findmain.py" "$APP")
[ -z "$MAIN" ] && { echo "  找不到主程序"; exit 1; }
echo "  主程序: $(basename "$MAIN")"
python3 "$HERE/inject.py" "$MAIN" TrollStoreJITEnabler.dylib

echo "[5/6] 删签名描述 + 重签"
find "$APP" -name "embedded.mobileprovision" -delete 2>/dev/null || true
python3 "$HERE/sign.py" "$APP"

echo "[6/6] 打包"
mkdir -p "$OUTDIR"
python3 "$HERE/pack.py" "$OUTDIR" "$WORK" manicemu-trollstore.ipa

echo
echo "=== 自检 ==="
python3 "$HERE/verify.py" "$OUTDIR/manicemu-trollstore.ipa" 1

echo
echo "=== 清理 build ==="
find "$WORK" -type f -delete 2>/dev/null || true
find "$WORK" -depth -type d -exec rmdir {} \; 2>/dev/null || true
rmdir "$WORK" 2>/dev/null || true
echo "完成"
