# wz

把课程资源站上的实验讲解视频批量下载到本地。

站点是「详情页 + HTML5 `<video>` 直链」的老式 ASP.NET 应用，登录带图片验证码。这个脚本做四件事：

1. 验证码登录并缓存会话（避免每次都看图）
2. 从列表页 / 详情页解析出所有视频直链与标题
3. 用 `yt-dlp` 断点续传地下载
4. 按课程分目录、同名文件自动编号、已完成的按大小校验后跳过

## 依赖

- Python 3.8+（**只用标准库**，没有 pip 依赖）
- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp)：`brew install yt-dlp`
- macOS / Linux / Windows（打开验证码图时自动用 `open` / `xdg-open` / 系统默认程序）

## 一键安装

下载/解压后，按系统选一个：

| 系统 | 做法 |
|---|---|
| **macOS** | 双击 `install.command`（或在终端 `bash install.sh`） |
| **Linux** | `bash install.sh` |
| **Windows** | 双击 `install.bat` |

安装脚本会自动完成这些事，**全程不需要 sudo**：

1. 检查 Python 3.8+（缺失时给出对应系统的安装指引）
2. 检查 `yt-dlp`，缺了就依次尝试 `brew` → `pip` → 下载官方单文件版
3. 把 `wz` 装到 `~/.local/bin`（Windows 是 `%LOCALAPPDATA%\wz`）
4. 补 `PATH`（macOS/Linux 写进 `~/.zshrc` 等，Windows 写用户级 PATH）
5. 自检 `wz --help`

装完**新开一个终端**，输入 `wz` 就能用。

> **macOS 提示「无法打开，因为来自身份不明的开发者」**：在解压出来的文件夹里执行
> `xattr -cr .` 清除隔离标记，或者右键 `install.command` → 打开。
>
> **Windows 提示「不是有效的 Win32 应用」**：一般是解压顺序错了，把整个 zip 完整解压后再双击 `install.bat`。

### 手动安装（不想跑脚本）

```bash
chmod +x wz_video_dl.py
ln -sf "$PWD/wz_video_dl.py" ~/.local/bin/wz
```

确认 `~/.local/bin` 在 `PATH` 里，然后 `wz --help`。

## 用法

```bash
wz                              # 列出所有课程
wz 1078                         # 按详情 ID 下载
wz '<详情页链接>'                # 直接贴 URL
wz '<课程列表页链接>'            # 整门课
wz all                          # 全部
wz -i 1078                      # 只看清单和总大小，不下载
wz -o ~/Movies/实验视频 1078     # 指定输出目录（默认 ~/Desktop/实验视频）
wz -j 3 all                     # 并发（对总带宽受限的站点没用）
wz -r 1078                      # 强制重新登录
```

## 配置

默认值已经指向本校站点和公共账号，不用改。要换站/换号，用环境变量覆盖（优先级高于脚本内的默认值）：

```bash
export WZ_BASE="http://<站点地址>"
export WZ_USER="<账号>"
export WZ_PWD="<密码>"
export WZ_OUT="$HOME/Movies/实验视频"     # 可选，改默认输出目录
```

Windows（PowerShell）：

```powershell
$env:WZ_BASE = "http://<站点地址>"
```

也可以直接改脚本顶部的同名常量。

## 说明

- **必须在内网 / VPN 环境下使用**，站点地址不对外解析。
- **验证码需要人工识别**：脚本会把图弹出来，你在终端敲 4 个字符。会话会缓存到 `~/.wz_session.json`（权限 600），过期才重新要码。
- 视频本体是静态文件，本身不校验登录态；登录只是为了拿到详情页里的链接。
- 已下载文件按远端大小校验，残缺文件会自动删除重下 —— `yt-dlp` 自己遇到同名文件会误报"已下载"。
- Windows 下命令是 `wz`（脚本会生成 `wz.cmd` 垫片），在 cmd / PowerShell / Windows Terminal 里都能直接调用。
- 下载内容的版权归原单位，仅供个人学习使用。
