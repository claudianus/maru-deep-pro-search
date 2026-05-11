#Requires -Version 5.1
<#
.SYNOPSIS
    One-click installer for maru-deep-pro-search on Windows.

.DESCRIPTION
    • Detects the system Python version.
    • If it is < 3.10, automatically installs Python 3.12 via uv.
    • Installs the package globally (uv tool install or pip --user).
    • Runs the setup wizard.
#>

$ErrorActionPreference = "Stop"

$MinPyMajor = 3
$MinPyMinor = 10
$TargetPy   = "$MinPyMajor.$MinPyMinor"

function Write-Title($text) { Write-Host $text -ForegroundColor Cyan -Bold }
function Write-Ok($text)    { Write-Host "  ✓ $text" -ForegroundColor Green }
function Write-Warn($text)  { Write-Host "  ! $text" -ForegroundColor Yellow }
function Write-Err($text)   { Write-Host "  ✗ $text" -ForegroundColor Red }

# ── 1. Discover Python ─────────────────────────────────────────
$pythonCmd = $null
$pythonVersion = $null

foreach ($cmd in @("python", "python3", "py")) {
    $found = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($found) {
        try {
            $verStr = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null
            if ($verStr) {
                $pythonCmd = $cmd
                $pythonVersion = $verStr
                break
            }
        } catch { continue }
    }
}

$pythonOk = $false
if ($pythonVersion) {
    $ver = [version]$pythonVersion
    if ($ver -ge [version]"$TargetPy.0") {
        $pythonOk = $true
    }
}

# ── 2. Discover uv ─────────────────────────────────────────────
$uvBin = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvBin) {
    $localUv = Join-Path $env:LOCALAPPDATA "programs\uv\uv.exe"
    if (Test-Path $localUv) { $uvBin = $localUv }
}

# ── 3. Decide strategy ─────────────────────────────────────────
$useUv = $false

Write-Host ""
Write-Title "📦 maru-deep-pro-search 설치를 시작합니다..."
Write-Host ""

if ($pythonOk) {
    Write-Ok "Python $pythonVersion detected"
    if ($uvBin) {
        Write-Ok "uv detected"
        $useUv = $true
    } else {
        Write-Host ""
        Write-Host "설치 방법을 선택하세요:"
        Write-Host "  1) pip  – 시스템 Python에 직접 설치"
        Write-Host "  2) uv   – 권장. 독립 환경에 설치되며 Python 버전 관리가 쉬움"
        $choice = Read-Host "선택 [1/2] (기본: 2)"
        if (-not $choice) { $choice = "2" }
        if ($choice -eq "2") { $useUv = $true }
    }
} else {
    if ($pythonVersion) {
        Write-Err "Python $pythonVersion detected (>=$TargetPy required)"
    } else {
        Write-Err "Python not found"
    }
    Write-Host ""
    Write-Host "이 프로젝트는 Python $TargetPy 이상이 필요합니다." -ForegroundColor Yellow
    Write-Host "→ uv를 사용해 자동으로 해결합니다." -ForegroundColor Yellow
    $useUv = $true
}

# ── 4. Ensure uv is installed ──────────────────────────────────
if ($useUv -and -not $uvBin) {
    Write-Host ""
    Write-Title "→ uv 설치 중..."
    Write-Host "   https://astral.sh/uv/install.ps1"
    irm https://astral.sh/uv/install.ps1 | iex

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    $uvBin = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uvBin) {
        $localUv = Join-Path $env:LOCALAPPDATA "programs\uv\uv.exe"
        if (Test-Path $localUv) { $uvBin = $localUv }
    }

    if (-not $uvBin) {
        Write-Host ""
        Write-Err "uv 설치에 실패했습니다."
        Write-Host "수동으로 PowerShell 관리자 권한에서 실행해 주세요:"
        Write-Host "   powershell -ExecutionPolicy ByPass -c `"irm https://astral.sh/uv/install.ps1 | iex`""
        exit 1
    }
    Write-Ok "uv 설치 완료"
}

# ── 5. Install the package ─────────────────────────────────────
Write-Host ""
if ($useUv) {
    Write-Title "→ uv로 설치합니다..."
    & $uvBin tool install --python $TargetPy --reinstall `
        "git+https://github.com/claudianus/maru-deep-pro-search.git"
} else {
    Write-Title "→ pip로 설치합니다..."
    & $pythonCmd -m pip install --user maru-deep-pro-search
}

# ── 6. Run setup wizard ────────────────────────────────────────
Write-Host ""
Write-Title "🚀 설정 마법사를 실행합니다..."
Write-Host ""
maru-deep-pro-search setup

# ── 7. Done ────────────────────────────────────────────────────
Write-Host ""
Write-Host "✅ 완료! AI 에이전트가 설정되었습니다." -ForegroundColor Green -Bold
Write-Host ""
Write-Host "사용 가능한 명령어:"
Write-Host "  maru-deep-pro-search setup        # 에이전트 재설정"
Write-Host "  maru-deep-pro-search setup --list # 설치된 에이전트 목록"
Write-Host ""
