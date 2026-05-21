#Requires -Version 5.1
<#
.SYNOPSIS
    Interactive installer for maru-deep-pro-search on Windows.

.DESCRIPTION
    • Detects the system Python version.
    • If it is < 3.10, guides the user through installing Python 3.12 via uv.
    • Installs the package globally from the GitHub repo.
    • Optionally runs the setup wizard.
#>

$ErrorActionPreference = "Stop"

$MinPyMajor = 3
$MinPyMinor = 10
$TargetPy   = "$MinPyMajor.$MinPyMinor"

# ── helpers ────────────────────────────────────────────────────
function Write-Title($text) { Write-Host "`n$text" -ForegroundColor Cyan -Bold }
function Write-Ok($text)    { Write-Host "  ✓ $text" -ForegroundColor Green }
function Write-Warn($text)  { Write-Host "  ! $text" -ForegroundColor Yellow }
function Write-Err($text)   { Write-Host "  ✗ $text" -ForegroundColor Red }
function Write-Info($text)  { Write-Host "  ℹ $text" -ForegroundColor Blue }

function Confirm($prompt, $default = "Y") {
    $choice = Read-Host "$prompt [$default]"
    if (-not $choice) { $choice = $default }
    return $choice -match '^[Yy]$'
}

# ── banner ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -Bold
Write-Host "║  📦 maru-deep-pro-search 설치를 시작합니다                  ║" -Bold
Write-Host "╚══════════════════════════════════════════════════════════════╝" -Bold
Write-Host ""

# ── 1. Discover Python ─────────────────────────────────────────
Write-Title "1. Python 환경 확인"
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

$useUv = $false
if ($pythonOk) {
    Write-Ok "Python $pythonVersion 사용 가능"
    Write-Info "이 버전으로 설치를 진행합니다."
} else {
    if ($pythonVersion) {
        Write-Err "Python $pythonVersion 감지됨 (>=$TargetPy 필요)"
    } else {
        Write-Err "Python not found"
    }
    Write-Host ""
    Write-Host "이 프로젝트는 Python $TargetPy 이상이 필요합니다." -ForegroundColor Yellow
    if (Confirm "uv를 사용해 Python $TargetPy를 자동 설치하시겠습니까?") {
        $useUv = $true
    } else {
        Write-Info "수동으로 Python $TargetPy를 설치한 후 다시 실행해 주세요."
        Write-Info "  https://www.python.org/downloads/"
        exit 1
    }
}

# ── 2. Discover uv ─────────────────────────────────────────────
$uvBin = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvBin) {
    $localUv = Join-Path $env:LOCALAPPDATA "programs\uv\uv.exe"
    if (Test-Path $localUv) { $uvBin = $localUv }
}

if ($pythonOk) {
    if ($uvBin) {
        Write-Ok "uv 감지됨"
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
}

# ── 3. Ensure uv is installed ──────────────────────────────────
if ($useUv -and -not $uvBin) {
    Write-Title "2. uv 설치"
    if (Confirm "uv가 필요합니다. 지금 설치하시겠습니까?") {
        Write-Host "   https://astral.sh/uv/install.ps1"
        irm https://astral.sh/uv/install.ps1 | iex

        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        $uvBin = Get-Command uv -ErrorAction SilentlyContinue
        if (-not $uvBin) {
            $localUv = Join-Path $env:LOCALAPPDATA "programs\uv\uv.exe"
            if (Test-Path $localUv) { $uvBin = $localUv }
        }

        if (-not $uvBin) {
            Write-Err "uv 설치에 실패했습니다."
            Write-Info "수동으로 실행해 주세요:"
            Write-Info "  powershell -ExecutionPolicy ByPass -c `"irm https://astral.sh/uv/install.ps1 | iex`""
            exit 1
        }
        Write-Ok "uv 설치 완료  ($uvBin)"
    } else {
        Write-Info "uv 설치 후 다시 실행해 주세요."
        Write-Info "  https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    }
}

# ── 4. Detect existing install ─────────────────────────────────
Write-Title "3. 기존 설치 확인"
$existing = Get-Command maru-deep-pro-search -ErrorAction SilentlyContinue
if ($existing) {
    try {
        $oldVer = & maru-deep-pro-search --version 2>$null
    } catch { $oldVer = "unknown" }
    Write-Warn "기존 설치 감지: $oldVer"
    Write-Info "GitHub 최신 코드로 교체합니다."
} else {
    Write-Info "기존 설치 없음"
}

# ── 5. Install the package ─────────────────────────────────────
Write-Title "4. 패키지 설치"
if ($useUv) {
    Write-Info "GitHub 저장소에서 최신 코드를 받습니다..."
    & $uvBin tool install --python $TargetPy --reinstall `
        "git+https://github.com/claudianus/maru-deep-pro-search.git"
} else {
    Write-Info "PyPI에서 설치합니다..."
    & $pythonCmd -m pip install --user "maru-deep-pro-search"
}

# Verify
try {
    $newVer = & maru-deep-pro-search --version 2>$null
} catch { $newVer = "unknown" }
Write-Ok "maru-deep-pro-search $newVer 설치 완료"

# ── 6. Hardware Detection ──────────────────────────────────────
Write-Title "5. 하드웨어 탐지"
Write-Info "시스템 사양을 분석합니다..."

$hwOutput = & $pythonCmd -c @"
import sys
sys.path.insert(0, 'src')
from maru_deep_pro_search.refiner.hardware import detect_hardware, get_optimal_model
hw = detect_hardware()
print(f'CPU: {hw.cpu_count} cores')
print(f'RAM: {hw.total_ram_mb // 1024} GB')
if hw.has_gpu:
    print(f'GPU: {hw.gpu_name} ({hw.gpu_vram_mb // 1024} GB VRAM)')
else:
    print('GPU: 없음 (CPU 추론)')
model = get_optimal_model(hw)
print(f'Recommended model: {model}')
"@ 2>$null

if ($LASTEXITCODE -eq 0) {
    $hwOutput | ForEach-Object { Write-Info $_ }
} else {
    Write-Warn "하드웨어 탐지 실패 (선택적 기능)"
}

# ── 7. llama-cpp-python GPU Wheel Selection ────────────────────
$nvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nvidiaSmi) {
    Write-Info "NVIDIA GPU 감지됨 — CUDA 가속 wheel 설치"
    & $pythonCmd -m pip install --force-reinstall llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu122
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "CUDA 가속 wheel 설치 완료"
    } else {
        Write-Warn "CUDA wheel 설치 실패 — CPU 모드로 동작합니다"
    }
}

# ── 8. Model Download ──────────────────────────────────────────
Write-Title "6. 경량 LLM 모델 다운로드"
Write-Info "콘텐츠 정제용 경량 모델을 다운로드합니다..."
Write-Info "이 모델은 웹 검색 결과를 깔끔하게 정리하여 토큰을 절약합니다."

$modelDownload = & $pythonCmd -c @"
import sys
sys.path.insert(0, 'src')
from maru_deep_pro_search.refiner.config import RefinerConfig, MODEL_REGISTRY
from maru_deep_pro_search.refiner.hardware import detect_hardware, get_optimal_model
from maru_deep_pro_search.refiner.model_manager import ModelManager

hw = detect_hardware()
model_name = get_optimal_model(hw)
config = RefinerConfig(model_name=model_name)
manager = ModelManager(config.cache_dir)

print(f'Selected model: {model_name}')
print(f'Size: {MODEL_REGISTRY[model_name]["size_mb"]} MB')
print('Downloading...')

try:
    path = manager.ensure_model(model_name)
    print(f'Model ready: {path}')
except Exception as e:
    print(f'Download failed: {e}', file=sys.stderr)
    sys.exit(1)
"@ 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Ok "모델 다운로드 완료"
} else {
    Write-Warn "모델 다운로드 실패 — 런타임에 자동으로 재시도됩니다"
}

# ── 9. Pre-download embedding model ────────────────────────────
Write-Title "7. 임베딩 모델 사전 다운로드"
Write-Info "첫 deep_research 지연 방지 — Hugging Face에서 Granite 임베딩을 받습니다."
$warmupOk = $false
if (Get-Command maru-deep-pro-search-setup -ErrorAction SilentlyContinue) {
    maru-deep-pro-search-setup warmup-embeddings -q
    if ($LASTEXITCODE -eq 0) { $warmupOk = $true }
} else {
    & $pythonCmd -m maru_deep_pro_search.cli.setup warmup-embeddings -q
    if ($LASTEXITCODE -eq 0) { $warmupOk = $true }
}
if ($warmupOk) {
    Write-Ok "임베딩 모델 준비 완료"
} else {
    Write-Warn "임베딩 모델 다운로드 실패 — 네트워크 확인 후 재실행:"
    Write-Info "  maru-deep-pro-search-setup warmup-embeddings"
}

# ── 10. Optional setup wizard ──────────────────────────────────
Write-Title "8. 설정 마법사"
Write-Host "설정 마법사는 AI 에이전트(Claude, Cursor, Kimi 등)를 자동 감지하고"
Write-Host "MCP 서버를 등록하는 과정입니다."
Write-Host ""
if (Confirm "지금 설정 마법사를 실행하시겠습니까?") {
    Write-Host ""
    maru-deep-pro-search setup
} else {
    Write-Info "설정은 나중에 직접 실행할 수 있습니다:"
    Write-Info "  maru-deep-pro-search setup"
}

# ── 11. Summary ────────────────────────────────────────────────
Write-Title "✅ 설치 완료 요약"
Write-Ok "Python: ${pythonVersion:-${TargetPy} (via uv)}"
Write-Ok "패키지: $newVer"
Write-Ok "설치 위치: $((Get-Command maru-deep-pro-search -ErrorAction SilentlyContinue).Source)"
Write-Host ""
Write-Host "사용 가능한 명령어:" -Bold
Write-Host "  maru-deep-pro-search setup         # 에이전트 설정"
Write-Host "  maru-deep-pro-search setup --list  # 설치된 에이전트 목록"
Write-Host "  maru-deep-pro-search init          # 프로젝트 하네스 초기화"
Write-Host "  maru-deep-pro-search --version     # 버전 확인"
Write-Host ""
