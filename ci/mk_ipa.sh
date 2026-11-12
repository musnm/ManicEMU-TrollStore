#!/bin/sh
# 打包成 TrollStore 可直装的未签名（ad-hoc 签名）IPA。
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

echo "----- 可执行文件 -----"
file "$BIN"
lipo -info "$BIN" || true

echo "----- 签名前校验 -----"
python3 ci/check_bundle.py "$APP_DIR" 2>/dev/null || true

# 清掉可能来自构建机的扩展属性
xattr -cr "$APP_DIR" 2>/dev/null || true

echo "----- ad-hoc 签名 -----"
ENT="/tmp/ent.plist"
cat > "$ENT" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>application-identifier</key>
	<string>TROLLTROLL.*</string>
	<key>com.apple.developer.team-identifier</key>
	<string>TROLLTROLL</string>
	<key>get-task-allow</key>
	<true/>
	<key>keychain-access-groups</key>
	<array>
		<string>TROLLTROLL.*</string>
	</array>
</dict>
</plist>
EOF

codesign --force --sign - --timestamp=none --entitlements "$ENT" "$APP_DIR" 2>&1 | tail -3 || \
    codesign --force --sign - --timestamp=none "$APP_DIR" 2>&1 | tail -3

echo "----- 签名验证 -----"
codesign -dv "$BIN" 2>&1 | head -8 || true
codesign --verify --verbose=2 "$APP_DIR" 2>&1 | tail -3 || true

echo "----- 打包后校验 -----"
python3 ci/check_bundle.py "$APP_DIR"

zip -qry "$TARGET_NAME.ipa" Payload
ls -lh "$TARGET_NAME.ipa"
shasum -a 256 "$TARGET_NAME.ipa"
