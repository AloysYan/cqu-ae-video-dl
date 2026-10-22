#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wz — 重庆大学 电子技术实验中心 资源共享平台 视频下载器

用法：
  wz                                 列出所有课程
  wz 1078                            按详情 ID 下载
  wz http://10.236.22.253/WZ/ZiYuanGongXiang/details/1078
  wz 'http://10.236.22.253/WZ/ZiYuanGongXiang?XueYuanId=...&KeChengId=...'
  wz -i 1078                         只看清单不下载
  wz all                             全部课程
  wz -j 3 1078                       3 个并发

依赖：python3（仅标准库）、yt-dlp
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = os.environ.get("WZ_BASE", "http://10.236.22.253").rstrip("/")

# 公共演示账号：学院公开分发给学生的资源站账号，不是个人凭据。
# 换站/换号可用环境变量覆盖：WZ_BASE / WZ_USER / WZ_PWD / WZ_OUT
USER = os.environ.get("WZ_USER", "20170001")
PWD = os.environ.get("WZ_PWD", "123456")

XUEYUAN_ID = "1604181156434889790"
DEFAULT_OUT = os.environ.get("WZ_OUT", os.path.join(
    os.path.expanduser("~"), "Desktop", "实验视频"))

# 会话文件里只有一个 ASP.NET_SessionId（约等于一张临时登录票据），固定 600
SESSION_FILE = os.path.join(os.path.expanduser("~"), ".wz_session.json")
SESSION_MODE = 0o600

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
VIDEO_EXT = (".mp4", ".flv", ".wmv", ".avi", ".mkv", ".mov", ".m4v")


# ------------------------------------------------------------------ 输出

def say(msg=""):
    print(msg, flush=True)


def human(n):
    if not n:
        return "?"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return ("%.0f %s" if unit == "B" else "%.1f %s") % (n, unit)
        n /= 1024.0


def _width(s):
    """按终端显示宽度算：中日韩字符占 2 列。"""
    return sum(2 if ord(c) > 0x2E7F else 1 for c in s)


def pad(s, n):
    return s + " " * max(0, n - _width(s))


def open_file(path):
    """跨平台打开文件：macOS 用 open，Windows 用 startfile，Linux 用 xdg-open。"""
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        elif os.name == "nt":
            os.startfile(path)          # noqa: 只在 Windows 存在
        else:
            subprocess.run(["xdg-open", path], check=False)
        return True
    except Exception:
        return False


# ------------------------------------------------------------------ HTTP

def _req(path, sid=None, data=None, ajax=False, referer=None, timeout=25):
    url = path if path.startswith("http") else BASE + path
    h = {"User-Agent": UA}
    if sid:
        h["Cookie"] = "ASP.NET_SessionId=" + sid
    if ajax:
        h["X-Requested-With"] = "XMLHttpRequest"
    if referer:
        h["Referer"] = referer
    body = urllib.parse.urlencode(data).encode() if data else None
    if body:
        h["Content-Type"] = "application/x-www-form-urlencoded"
    with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=h),
                                timeout=timeout) as r:
        return r.read().decode("utf-8", "replace"), (r.getheader("Set-Cookie") or "")


def _sid_of(set_cookie):
    m = re.search(r"ASP\.NET_SessionId=([^;]+)", set_cookie)
    return m.group(1) if m else None


# ------------------------------------------------------------------ 登录

def _grab_captcha(sid, path):
    """取验证码图。注意：站点**只有**这个接口会下发 ASP.NET_SessionId，
    所以首次调用必须不带 cookie，并同时把会话 ID 收下来。"""
    h = {"User-Agent": UA, "Referer": BASE + "/WZ/Shared/Login"}
    if sid:
        h["Cookie"] = "ASP.NET_SessionId=" + sid
    req = urllib.request.Request(BASE + "/WZ/Shared/PicCk?v=%f" % time.time(), headers=h)
    with urllib.request.urlopen(req, timeout=20) as r:
        data = r.read()
        new_sid = _sid_of(r.getheader("Set-Cookie") or "")
    with open(path, "wb") as f:
        f.write(data)
    return new_sid or sid


def do_login():
    """验证码登录；验证码错了会重来，最多 3 次。临时图用完即删。"""
    say("→ 建立会话…")
    sid = None
    # mkstemp 默认就是 0600，别人读不到；退出前删掉
    fd, cap = tempfile.mkstemp(prefix="wz_captcha_", suffix=".png")
    os.close(fd)
    try:
        for attempt in range(1, 4):
            sid = _grab_captcha(sid, cap)
            if not sid:
                sys.exit("× 验证码接口没有下发 ASP.NET_SessionId，站点行为可能变了")
            if not open_file(cap):
                say("  打不开图片，请手动查看：%s" % cap)
            code = input("→ 验证码图已弹出(%d/3)，输入后回车：" % attempt).strip()
            if not code:
                continue
            txt, sc2 = _req("/WZ/Shared/Login", sid=sid, ajax=True,
                            referer=BASE + "/WZ/Shared/Login",
                            data={"YHM": USER, "MM": PWD, "yz": code, "dl_tj": "登录"})
            try:
                j = json.loads(txt)
            except Exception:
                say("× 返回非 JSON：%s" % txt[:120])
                continue
            if j.get("Statu") == "ok":
                say("✓ " + j.get("Msg", "登录成功"))
                return _sid_of(sc2) or sid
            say("× " + str(j.get("Msg", "登录失败")))
        sys.exit("× 登录连续失败，放弃")
    finally:
        try:
            os.remove(cap)
        except OSError:
            pass


def session_ok(sid):
    """登录后页面才会出现退出链接，用它判活，不依赖任何具体资源 ID。"""
    try:
        html, _ = _req("/WZ/Home/Index", sid=sid)
        return "TuiChuLogin" in html
    except Exception:
        return False


def _save_session(sid):
    """会话票据按 600 写盘，避免同机其他账户拿去冒用登录态。"""
    try:
        fd = os.open(SESSION_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, SESSION_MODE)
        with os.fdopen(fd, "w") as f:
            json.dump({"sid": sid, "ts": time.time()}, f)
        os.chmod(SESSION_FILE, SESSION_MODE)
    except Exception:
        pass


def get_session(force=False):
    if not force and os.path.exists(SESSION_FILE):
        try:
            if os.stat(SESSION_FILE).st_mode & 0o077:   # 权限过宽 → 收紧
                os.chmod(SESSION_FILE, SESSION_MODE)
            with open(SESSION_FILE) as f:
                sid = json.load(f).get("sid")
            if sid and session_ok(sid):
                say("✓ 复用已保存的登录态")
                return sid
        except Exception:
            pass
    sid = do_login()
    _save_session(sid)
    return sid


# ------------------------------------------------------------------ 抓取

def parse_courses(sid):
    html, _ = _req("/WZ/ZiYuanGongXiang", sid=sid)
    return dict((cid, name.strip()) for cid, name in
                re.findall(r'KeChengId=(\d+)">([^<]+)', html))


def parse_resources(sid, course_id=None):
    path = "/WZ/ZiYuanGongXiang"
    if course_id:
        path += "?XueYuanId=%s&KeChengId=%s" % (XUEYUAN_ID, course_id)
    html, _ = _req(path, sid=sid)
    seen, out = set(), []
    for i in re.findall(r'/WZ/ZiYuanGongXiang/details/(\d+)', html):
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def parse_videos(sid, detail_id):
    """详情页：<video src> 后面紧跟 <span title="大小 ...">文件名</span>。"""
    html, _ = _req("/WZ/ZiYuanGongXiang/details/%s" % detail_id, sid=sid)
    out = []
    for m in re.finditer(r'<video[^>]*src="([^"]+)"(.*?)</video>(.*?)</span>', html, re.S):
        src, tail = m.group(1), m.group(3)
        name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", tail)).strip()
        if not name.lower().endswith(VIDEO_EXT):
            name = os.path.basename(src)
        out.append((name, src if src.startswith("http") else BASE + src))
    return out


def course_of(sid, detail_id, courses):
    """反查某个详情页属于哪门课，用于决定输出子目录名。"""
    for cid, name in courses.items():
        try:
            if detail_id in parse_resources(sid, cid):
                return name
        except Exception:
            continue
    return None


# ------------------------------------------------------------------ 工具

def safe_name(s):
    return re.sub(r'[\\/:*?"<>|]', "_", s).strip() or "未命名"


def remote_size(url, referer=BASE + "/WZ/ZiYuanGongXiang"):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer,
                                                   "Range": "bytes=0-0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            cr = r.headers.get("Content-Range") or ""
            m = re.search(r"/(\d+)$", cr)
            if m:
                return int(m.group(1))
            cl = r.headers.get("Content-Length")
            return int(cl) if cl and cl.isdigit() and int(cl) > 1 else 0
    except Exception:
        return 0


def classify(arg):
    a = arg.strip()
    if a.lower() in ("all", "全", "全部"):
        return ("all", None)
    m = re.search(r"/details/(\d+)", a)
    if m:
        return ("detail", m.group(1))
    m = re.search(r"[?&]KeChengId=(\d+)", a)
    if m:
        return ("course", m.group(1))
    if re.fullmatch(r"\d+", a):
        return ("detail", a)
    if "ZiYuanGongXiang" in a:
        return ("list", None)
    raise SystemExit("× 认不出这个参数：%s\n  支持：详情 ID / details 链接 / 课程链接 / all" % a)


# ------------------------------------------------------------------ 下载

def ytdlp_prefix():
    """找到 yt-dlp：优先 PATH 里的可执行文件，其次当前解释器的 yt_dlp 模块。"""
    exe = shutil.which("yt-dlp")
    if exe:
        return [exe]
    try:
        import yt_dlp  # noqa: F401
        return [sys.executable, "-m", "yt_dlp"]
    except Exception:
        return None


def ytdlp(url, target, referer, quiet=False):
    prefix = ytdlp_prefix()
    if not prefix:
        say("  ! 找不到 yt-dlp，请先安装：brew install yt-dlp  或  pip install -U yt-dlp")
        return False
    cmd = prefix + ["--referer", referer, "--user-agent", UA,
                    "--continue", "--retries", "10", "--fragment-retries", "10",
                    "--socket-timeout", "30", "--no-warnings"]
    if quiet:
        cmd += ["--quiet", "--no-progress"]
    cmd += ["-o", target, url]
    return subprocess.call(cmd, stdout=(subprocess.DEVNULL if quiet else None),
                           stderr=(subprocess.DEVNULL if quiet else None)) == 0


def run_one(job, out_root, quiet):
    tag, name, url, expect = job
    outdir = os.path.join(out_root, safe_name(tag))
    target = os.path.join(outdir, safe_name(name))
    os.makedirs(outdir, exist_ok=True)

    # 本地已存在 → 必须比对远端大小，否则半截文件会被 yt-dlp 误判"已下载"
    if os.path.exists(target):
        ls = os.path.getsize(target)
        if expect and ls == expect:
            return ("skip", name, 0)
        say("  ~ %s 本地 %s ≠ 远端 %s，删除重下" % (name, human(ls), human(expect)))
        try:
            os.remove(target)
        except OSError:
            pass

    ok = ytdlp(url, target, BASE + "/WZ/ZiYuanGongXiang", quiet=quiet)
    size = os.path.getsize(target) if os.path.exists(target) else 0
    if ok and expect and size != expect:
        say("  ! %s 大小不符：%s ≠ %s" % (name, human(size), human(expect)))
        return ("fail", name, size)
    return ("ok" if ok else "fail", name, size)


# ------------------------------------------------------------------ 主流程

def main():
    ap = argparse.ArgumentParser(
        prog="wz", description="重庆大学电子技术实验中心 资源共享平台 视频下载器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="例：wz 1078   |   wz -i 'http://10.236.22.253/WZ/ZiYuanGongXiang/details/1078'   |   wz all")
    ap.add_argument("target", nargs="*", help="详情 ID / details 链接 / 课程链接 / all")
    ap.add_argument("-i", "--info", action="store_true", help="只列清单，不下载")
    ap.add_argument("-o", "--out", default=DEFAULT_OUT, help="输出目录（默认 %s）" % DEFAULT_OUT)
    ap.add_argument("-j", "--jobs", type=int, default=1, help="并发数（默认 1）")
    ap.add_argument("-r", "--relogin", action="store_true", help="强制重新登录")
    ap.add_argument("-l", "--list", action="store_true", help="列出所有课程")
    args = ap.parse_args()

    sid = get_session(force=args.relogin)
    courses = parse_courses(sid)

    if args.list or (not args.target and not args.info):
        say("\n课程列表：")
        for cid, name in courses.items():
            n = len(parse_resources(sid, cid))
            say("  %s  %2d 个资源   KeChengId=%s" % (pad(name, 30), n, cid))
        say("\n用法：wz <详情ID|链接>   或   wz '<课程链接>'   或   wz all")
        say("      wz -i 1078  先看清单再决定")
        return

    # 目标资源
    targets = []   # (展示名, detail_id)
    for t in args.target:
        kind, val = classify(t)
        if kind == "detail":
            tag = course_of(sid, val, courses) or ("资源_%s" % val)
            targets.append((tag, val))
        elif kind == "course":
            for did in parse_resources(sid, val):
                targets.append((courses.get(val, "课程_%s" % val), did))
        elif kind == "all":
            for cid, name in courses.items():
                for did in parse_resources(sid, cid):
                    targets.append((name, did))
        else:  # 无过滤的列表页
            for did in parse_resources(sid, None):
                targets.append((course_of(sid, did, courses) or "未分类", did))

    if not targets:
        say("× 没有解析到任何资源")
        return

    say("\n→ %d 个资源条目，解析视频直链…" % len(targets))
    jobs = []   # (展示名, 文件名, 直链)
    for tag, did in targets:
        try:
            vids = parse_videos(sid, did)
        except Exception as e:
            say("  ! %s/%s 解析失败：%s" % (tag, did, e))
            continue
        say("  %s /%s → %d 个视频" % (pad(tag, 28), did, len(vids)))
        for name, url in vids:
            jobs.append((tag, name, url))

    # 直链去重
    seen, uniq = set(), []
    for j in jobs:
        if j[2] not in seen:
            seen.add(j[2])
            uniq.append(j)
    jobs = uniq

    # 同名不同源 → 加序号
    used, fixed = set(), []
    for tag, name, url in jobs:
        key = (safe_name(tag), safe_name(name).lower())
        if key in used:
            stem, ext = os.path.splitext(name)
            n = 2
            while (safe_name(tag), safe_name("%s (%d)%s" % (stem, n, ext)).lower()) in used:
                n += 1
            name = "%s (%d)%s" % (stem, n, ext)
            key = (safe_name(tag), safe_name(name).lower())
        used.add(key)
        fixed.append((tag, name, url))
    jobs = fixed

    # 预估总大小
    say("\n  统计大小…")
    total = 0
    sized = []
    for tag, name, url in jobs:
        sz = remote_size(url)
        total += sz
        sized.append((tag, name, url, sz))
    jobs = sized

    say("\n=== 共 %d 个视频，总计 %s ===" % (len(jobs), human(total)))
    for tag, name, url, sz in jobs:
        say("  [%s] %s  (%s)" % (tag, name, human(sz)))

    if args.info:
        return

    say("\n输出到：%s" % args.out)
    t0 = time.time()
    ok = skip = fail = 0
    done_bytes = 0

    if args.jobs > 1:
        say("→ %d 并发下载（静默模式，逐条报结果）\n" % args.jobs)
        with ThreadPoolExecutor(max_workers=args.jobs) as ex:
            futs = {ex.submit(run_one, (t, n, u, s), args.out, True): (t, n, s)
                    for t, n, u, s in jobs}
            for i, f in enumerate(as_completed(futs), 1):
                tag, name, _ = futs[f]
                try:
                    st, n2, size = f.result()
                except Exception as e:
                    st, n2, size = "fail", name, 0
                    say("  ! %s：%s" % (name, e))
                if st == "ok":
                    done_bytes += size
                    ok += 1
                    say("[%d/%d] ✓ %s (%s)" % (i, len(jobs), n2, human(size)))
                elif st == "skip":
                    skip += 1
                    say("[%d/%d] = %s 已存在" % (i, len(jobs), n2))
                else:
                    fail += 1
                    say("[%d/%d] × %s 失败" % (i, len(jobs), n2))
    else:
        for i, (tag, name, url, sz) in enumerate(jobs, 1):
            say("\n[%d/%d] %s" % (i, len(jobs), name))
            st, n2, size = run_one((tag, name, url, sz), args.out, False)
            if st == "ok":
                done_bytes += size
                ok += 1
            elif st == "skip":
                skip += 1
                say("  已存在且大小一致，跳过")
            else:
                fail += 1
                say("  ! 失败，可重跑（支持断点续传）")

    dt = max(time.time() - t0, 0.01)
    say("\n=== 完成：成功 %d / 跳过 %d / 失败 %d ===" % (ok, skip, fail))
    say("共 %s，用时 %.0f 秒，平均 %s/s" % (human(done_bytes), dt, human(done_bytes / dt)))
    if fail:
        say("有失败项，重跑同一条命令即可续传")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        say("\n已中断。重跑同一条命令可断点续传。")
        sys.exit(130)
