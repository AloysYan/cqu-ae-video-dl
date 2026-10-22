#!/usr/bin/env bash
# macOS 双击运行入口。相当于在终端里执行 bash install.sh

cd "$(dirname "$0")" || exit 1
bash ./install.sh "$@"
STATUS=$?

printf '\n'
if [ "$STATUS" -ne 0 ]; then
    printf '安装没有成功，把上面的输出截图发给分享者。\n'
else
    printf '可以关掉这个窗口了。新开一个终端，输入 wz 试试。\n'
fi
printf '按任意键关闭…'
read -n 1 -s -r
printf '\n'
