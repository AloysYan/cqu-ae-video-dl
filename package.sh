#!/usr/bin/env bash
# 打发布包：按操作系统各出一个 zip，放到 dist/
#
#   bash package.sh            # 版本号默认读 VERSION，否则 1.0.0
#   bash package.sh 1.0.1      # 指定版本

set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SRC_DIR"

VER="${1:-$(cat VERSION 2>/dev/null || echo 1.0.0)}"
DIST="$SRC_DIR/dist"
COMMON="wz_video_dl.py README.md"

G=$'\033[32m'; N=$'\033[0m'
ok() { printf '%s✓%s %s\n' "$G" "$N" "$*"; }

# Windows 的 .bat 必须是 CRLF，否则 cmd 解析标签/多行会出怪问题
to_crlf() { sed -e 's/$/\r/' "$1" > "$2"; }

rm -rf "$DIST"
mkdir -p "$DIST"

# $1=平台后缀  $2...=该平台额外要带的文件
build() {
    local os="$1"; shift
    local name="wz-${VER}-${os}"
    local stage="$DIST/.stage/$name"
    mkdir -p "$stage"

    cp $COMMON "$stage/"
    chmod +x "$stage/wz_video_dl.py"
    for f in "$@"; do
        if [ "$f" = "install.bat" ]; then
            to_crlf "install.bat" "$stage/install.bat"
        else
            cp "$f" "$stage/"
        fi
    done
    chmod +x "$stage"/install.sh "$stage"/install.command 2>/dev/null || true

    ( cd "$DIST/.stage" && zip -qr -X "$DIST/$name.zip" "$name" )
    rm -rf "$DIST/.stage"
    ok "$name.zip  ($(du -h "$DIST/$name.zip" | cut -f1 | tr -d ' '))"
}

echo "打包版本 v${VER}"
build macos  install.sh install.command
build linux  install.sh
build windows install.bat install.ps1

echo
echo "校验值："
( cd "$DIST" && shasum -a 256 *.zip )

echo
echo "产物在 $DIST"
