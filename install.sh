#!/usr/bin/env bash
# wz 一键安装（macOS / Linux）
#
#   bash install.sh            默认复制安装到 ~/.local/bin/wz
#   bash install.sh --link     改用软链（开发用，改源码即生效）
#
# 全程不需要 sudo，所有东西只写在自己的 home 目录里。

set -uo pipefail

BIN_DIR="$HOME/.local/bin"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$SRC_DIR/wz_video_dl.py"
TARGET="$BIN_DIR/wz"
MODE="copy"

for arg in "$@"; do
    case "$arg" in
        --link) MODE="link" ;;
        -h|--help) sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    esac
done

if [ -t 1 ]; then
    G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[31m'; D=$'\033[90m'; B=$'\033[1m'; N=$'\033[0m'
else
    G=""; Y=""; R=""; D=""; B=""; N=""
fi

ok()   { printf '%s✓%s %s\n' "$G" "$N" "$*"; }
skip() { printf '%s·%s %s\n' "$D" "$N" "$*"; }
warn() { printf '%s!%s %s\n' "$Y" "$N" "$*"; }
die()  { printf '%s×%s %s\n' "$R" "$N" "$*" >&2; exit 1; }
step() { printf '\n%s%s%s\n' "$B" "$*" "$N"; }

printf '%s\n' "=============================================="
printf '%s\n' "  wz 安装程序 —— 课程资源站视频下载器"
printf '%s\n' "=============================================="

[ -f "$SRC" ] || die "找不到 wz_video_dl.py，请把安装包完整解压后再运行"

# ---------------------------------------------------------------- 1. Python
step "1/4 检查 Python"
PY=""
if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys;sys.exit(0 if sys.version_info>=(3,8) else 1)' 2>/dev/null; then
    PY="python3"
    ok "python3 $(python3 -c 'import sys;print("%d.%d.%d"%sys.version_info[:3])')"
else
    warn "没找到 python3（需要 3.8 以上）"
    if [ "$(uname -s)" = "Darwin" ]; then
        echo "  macOS 上最省事的办法是装命令行工具（弹窗点“安装”即可）："
        echo "      xcode-select --install"
        echo "  或者用 Homebrew：brew install python"
        if xcode-select -p >/dev/null 2>&1; then
            echo "  检测到命令行工具已安装，可能只是 python3 不在 PATH 里。"
        fi
    else
        echo "  Debian/Ubuntu：sudo apt install python3"
        echo "  Fedora：sudo dnf install python3"
    fi
    die "请先装好 Python 3.8+ 再重新运行本脚本"
fi

# ---------------------------------------------------------------- 2. yt-dlp
step "2/4 检查 yt-dlp"
if command -v yt-dlp >/dev/null 2>&1; then
    ok "yt-dlp $(yt-dlp --version 2>/dev/null)"
elif "$PY" -c 'import yt_dlp' 2>/dev/null; then
    ok "yt-dlp 模块已装（用 python -m yt_dlp 调用）"
else
    skip "未安装，开始自动安装…"
    installed=0

    if command -v brew >/dev/null 2>&1; then
        printf '  尝试 Homebrew 安装…\n'
        if brew install yt-dlp; then installed=1; fi
    fi

    if [ "$installed" -eq 0 ] && "$PY" -m pip --version >/dev/null 2>&1; then
        printf '  尝试 pip 安装…\n'
        if "$PY" -m pip install --user -U yt-dlp >/dev/null 2>&1 \
           || "$PY" -m pip install --user -U yt-dlp --break-system-packages >/dev/null 2>&1; then
            installed=1
        fi
    fi

    if [ "$installed" -eq 0 ]; then
        printf '  尝试下载官方单文件版…\n'
        mkdir -p "$BIN_DIR"
        case "$(uname -s)-$(uname -m)" in
            Darwin-*)          ASSET="yt-dlp_macos" ;;
            Linux-x86_64)      ASSET="yt-dlp_linux" ;;
            Linux-aarch64|Linux-arm64) ASSET="yt-dlp_linux_aarch64" ;;
            *)                 ASSET="" ;;
        esac
        if [ -n "$ASSET" ] && command -v curl >/dev/null 2>&1; then
            URL="https://github.com/yt-dlp/yt-dlp/releases/latest/download/${ASSET}"
            TMPDL="${BIN_DIR}/.yt-dlp.download"
            rm -f "$TMPDL"
            # 先下到临时名，能跑起来才正式落位，避免中断留下半截可执行文件
            if curl -fL --retry 3 --connect-timeout 20 --progress-bar "$URL" -o "$TMPDL" \
               && [ -s "$TMPDL" ] && chmod +x "$TMPDL" \
               && "$TMPDL" --version >/dev/null 2>&1; then
                mv -f "$TMPDL" "${BIN_DIR}/yt-dlp"
                installed=1
            else
                rm -f "$TMPDL"
                warn "单文件版下载失败（可能是网络受限）"
            fi
        fi
    fi

    if [ "$installed" -eq 1 ]; then
        if command -v yt-dlp >/dev/null 2>&1; then
            ok "yt-dlp $(yt-dlp --version 2>/dev/null)"
        elif "$PY" -c 'import yt_dlp' 2>/dev/null; then
            ok "yt-dlp 模块已装"
        else
            ok "yt-dlp 已装到 ${BIN_DIR}（重新打开终端后生效）"
        fi
    else
        die "yt-dlp 自动安装失败。请手动执行：brew install yt-dlp  或  pip install -U yt-dlp"
    fi
fi

# ---------------------------------------------------------------- 3. 安装本体
step "3/4 安装 wz 命令"
mkdir -p "$BIN_DIR" || die "无法创建 $BIN_DIR"

if [ -e "$TARGET" ] || [ -L "$TARGET" ]; then
    skip "已存在 ${TARGET}，将被覆盖"
    rm -f "$TARGET"
fi

if [ "$MODE" = "link" ]; then
    ln -s "$SRC" "$TARGET" || die "创建软链失败"
    ok "已软链 ${TARGET} -> ${SRC}"
else
    cp "$SRC" "$TARGET" || die "复制失败"
    ok "已安装 ${TARGET}"
fi
chmod +x "$TARGET"

# ---------------------------------------------------------------- 4. PATH
step "4/4 检查 PATH"
case ":$PATH:" in
    *":$BIN_DIR:"*)
        ok "${BIN_DIR} 已在 PATH 中"
        ;;
    *)
        RC=""
        case "$(basename "${SHELL:-bash}")" in
            zsh)  RC="$HOME/.zshrc" ;;
            bash) [ -f "$HOME/.bashrc" ] && RC="$HOME/.bashrc" || RC="$HOME/.bash_profile" ;;
            *)    RC="$HOME/.profile" ;;
        esac
        LINE="export PATH=\"\$HOME/.local/bin:\$PATH\"  # added by wz installer"
        if [ -n "$RC" ] && grep -qF "# added by wz installer" "$RC" 2>/dev/null; then
            skip "${RC} 里已有配置，跳过"
        elif [ -n "$RC" ]; then
            printf '\n%s\n' "$LINE" >> "$RC"
            ok "已把 ${BIN_DIR} 写入 ${RC}"
        fi
        export PATH="$BIN_DIR:$PATH"
        ;;
esac

# ---------------------------------------------------------------- 自检
printf '\n'
if "$TARGET" --help >/dev/null 2>&1; then
    ok "自检通过，命令可用"
else
    warn "自检未通过，请把上面的报错发出来"
fi

step "安装完成"
printf '  用法：\n'
printf '    %s\n' "wz                     列出课程" "wz 1078                按详情 ID 下载" "wz '<页面链接>'        直接贴链接" "wz -i 1078             只看清单" "wz all                 全部下载"
printf '\n'
printf '  %s\n' "提示：本工具需要连着校园网（或学校 VPN）才能访问站点。"
if [ -n "${RC:-}" ]; then
    printf '  %s\n' "新开的终端窗口才会自动带上 PATH；当前窗口可以先执行：source ${RC}"
fi
printf '\n'
