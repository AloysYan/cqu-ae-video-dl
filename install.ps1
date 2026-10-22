# wz 一键安装（Windows PowerShell 5.1+）
# 由 install.bat 调用，也可手动运行：
#   powershell -NoProfile -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}

$srcDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$src    = Join-Path $srcDir "wz_video_dl.py"
$dest   = Join-Path $env:LOCALAPPDATA "wz"

function Ok($m)   { Write-Host "OK   $m" -ForegroundColor Green }
function Skip($m) { Write-Host "--   $m" -ForegroundColor DarkGray }
function Warn($m) { Write-Host "!    $m" -ForegroundColor Yellow }
function Die($m)  { Write-Host "X    $m" -ForegroundColor Red; exit 1 }
function Step($m) { Write-Host ""; Write-Host $m -ForegroundColor White }

Write-Host "=============================================="
Write-Host "  wz installer - course video downloader"
Write-Host "=============================================="

if (-not (Test-Path $src)) { Die "wz_video_dl.py not found. Please extract the whole zip first." }

# ------------------------------------------------------------------ 1. Python
Step "[1/4] Checking Python"
$pyCmd = $null

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -c "import sys;sys.exit(0 if sys.version_info>=(3,8) else 1)" 2>$null
    if ($LASTEXITCODE -eq 0) { $pyCmd = @("py", "-3") }
}
if (-not $pyCmd) {
    foreach ($n in @("python", "python3")) {
        if (Get-Command $n -ErrorAction SilentlyContinue) {
            & $n -c "import sys;sys.exit(0 if sys.version_info>=(3,8) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) { $pyCmd = @($n); break }
        }
    }
}

if (-not $pyCmd) {
    Warn "Python 3.8+ not found."
    Write-Host "  Download it from https://www.python.org/downloads/windows/"
    Write-Host "  IMPORTANT: tick 'Add python.exe to PATH' during setup."
    Write-Host "  Then run install.bat again."
    Start-Process "https://www.python.org/downloads/windows/"
    exit 1
}

$pyVer = & $pyCmd[0] @($pyCmd[1..($pyCmd.Length - 1)] + @("-c", "import sys;print('%d.%d.%d'%sys.version_info[:3])"))
Ok "Python $pyVer"

function Run-Py([string[]]$extra) {
    $all = $pyCmd + $extra
    & $all[0] @($all[1..($all.Length - 1)])
    return $LASTEXITCODE
}

# ------------------------------------------------------------------ 2. yt-dlp
Step "[2/4] Checking yt-dlp"
$hasYtdlp = $false

if (Get-Command yt-dlp -ErrorAction SilentlyContinue) {
    $v = (yt-dlp --version 2>$null)
    Ok "yt-dlp $v"
    $hasYtdlp = $true
} else {
    $rc = Run-Py @("-c", "import yt_dlp")
    if ($rc -eq 0) { Ok "yt-dlp module ready"; $hasYtdlp = $true }
}

if (-not $hasYtdlp) {
    Skip "not installed, installing via pip..."
    $rc = Run-Py @("-m", "pip", "install", "--upgrade", "--user", "yt-dlp")
    if ($rc -ne 0) { $rc = Run-Py @("-m", "pip", "install", "--upgrade", "yt-dlp") }
    if ($rc -eq 0) { Ok "yt-dlp installed" }
    else { Die "pip install failed. Run manually: python -m pip install --upgrade yt-dlp" }
}

# ------------------------------------------------------------------ 3. 安装本体
Step "[3/4] Installing wz"
if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Path $dest -Force | Out-Null }
Copy-Item $src (Join-Path $dest "wz.py") -Force
Ok "copied to $dest\wz.py"

$pyExe = ($pyCmd -join " ")
$shim = @"
@echo off
chcp 65001 >nul
$pyExe "$dest\wz.py" %*
"@
Set-Content -Path (Join-Path $dest "wz.cmd") -Value $shim -Encoding ASCII
Ok "launcher: $dest\wz.cmd"

# ------------------------------------------------------------------ 4. PATH
Step "[4/4] Checking PATH"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($null -eq $userPath) { $userPath = "" }
if ($userPath -split ';' -contains $dest) {
    Ok "$dest already in PATH"
} else {
    [Environment]::SetEnvironmentVariable("Path", ($dest.TrimEnd(';') + ";" + $userPath).TrimEnd(';'), "User")
    Ok "added $dest to user PATH"
}
$env:Path = "$dest;$env:Path"

# ------------------------------------------------------------------ 自检
Write-Host ""
$h = & (Join-Path $dest "wz.cmd") --help 2>&1
if ($LASTEXITCODE -eq 0) { Ok "self-check passed" } else { Warn "self-check failed, see output above" }

Step "Done"
Write-Host "  wz                  list courses"
Write-Host "  wz 1078             download by detail id"
Write-Host "  wz <url>            paste any page url"
Write-Host "  wz -i 1078          list only"
Write-Host "  wz all              download everything"
Write-Host ""
Write-Host "  Note: campus network or school VPN is required."
Write-Host "  Open a NEW terminal window for the PATH change to take effect."
Write-Host ""
