## 依赖

- Python 3.8+
- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp)：`brew install yt-dlp`
- macOS / Linux / Windows

## 一键安装

下载/解压后，按系统选一个：

| 系统 | 做法 |
|---|---|
| **macOS** | 双击 `install.command`（或在终端 `bash install.sh`） |
| **Linux** | `bash install.sh` |
| **Windows** | 双击 `install.bat` |

装完**新开一个终端**，输入 `wz` 就能用。

> **macOS 提示「无法打开，因为来自身份不明的开发者」**：在解压出来的文件夹里执行
> `xattr -cr .` 清除隔离标记，或者右键 `install.command` → 打开。
>
> **Windows 提示「不是有效的 Win32 应用」**：一般是解压顺序错了，把整个 zip 完整解压后再双击 `install.bat`。

## 用法

```bash
wz                              # 列出所有课程
wz 1078                         # 按详情 ID 下载
wz '<详情页链接>'                 # 直接贴 URL
wz '<课程列表页链接>'             # 整门课
wz all                          # 全部
wz -i 1078                      # 只看清单和总大小，不下载
wz -o ~/Movies/实验视频 1078     # 指定输出目录（默认 ~/Desktop/实验视频）
wz -j 3 all                     # 并发（对总带宽受限的站点没用）
wz -r 1078                      # 强制重新登录
```

## 说明

- **必须在校园网环境下使用**
- **验证码需要人工识别**：脚本把图弹出来后，在终端敲字符。会话会缓存到 `~/.wz_session.json`（权限 600），过期重新要码。
- 视频本体是静态文件，本身不校验登录态；登录只是为了拿到详情页里的链接。
- 已下载文件按远端大小校验，残缺文件会自动删除重下 —— `yt-dlp` 自己遇到同名文件会误报"已下载"。
- Windows 下命令是 `wz`（脚本会生成 `wz.cmd` 垫片），在 cmd / PowerShell / Windows Terminal 里都能直接调用。
- 下载内容的版权归原单位，仅供个人学习使用。
