#!/bin/sh
# 把 CgBI(Apple 压缩) PNG 转回标准 PNG。
#
# cocos2d-x 的 ios 模板图标是 pngcrush 处理过的 CgBI 格式，只有 Apple 的
# 解码链路（或 PNG 解码时显式支持 CgBI）才认得。非 Apple 工具链打包、
# 又原样塞进 bundle 时，SpringBoard 解不出图像 → 桌面无图标。
#
# 用 macOS 自带 sips 重新编码即可得到标准 PNG。
set -e

APP="$1"
[ -d "$APP" ] || { echo "用法: $0 <App.app>"; exit 1; }

count=0
for f in "$APP"/*.png; do
    [ -f "$f" ] || continue
    if head -c 16 "$f" | grep -q CgBI 2>/dev/null; then
        tmp="$f.tmp.png"
        # sips 读 CgBI 后按标准 PNG 写出
        if sips -s format png "$f" --out "$tmp" >/dev/null 2>&1; then
            mv "$tmp" "$f"
            count=$((count + 1))
        else
            rm -f "$tmp"
            echo "  [!] 转换失败: $f"
        fi
    fi
done

echo "[*] CgBI -> 标准 PNG: $count 个"
