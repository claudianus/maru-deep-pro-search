#!/bin/bash
# One-click installer for maru-deep-pro-search
#
# Goals:
#   • Detect the system Python version.
#   • If it is < 3.10, guide the user through installing Python 3.12 via uv.
#   • Install the package so the CLI is available globally.
#   • Optionally run the setup wizard.
#
# Usage:
#   curl -LsSf https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.sh | sh

set -e

# When this script is run via pipe (curl | bash), child processes inherit the
# same pipe as stdin.  That breaks MCP servers which read JSON-RPC from stdin.
# Fix: dump the script to a temp file and re-exec from there so children get
# a clean stdin (the real TTY or /dev/null, not the script stream).
if [ ! -t 0 ] && [ -p /dev/stdin ]; then
    _tmp=$(mktemp)
    cat > "$_tmp"
    chmod +x "$_tmp"
    exec bash "$_tmp" "$@"
fi

MIN_PY_MAJOR=3
MIN_PY_MINOR=10
TARGET_PY="${MIN_PY_MAJOR}.${MIN_PY_MINOR}"

# ── colours ────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── helpers ────────────────────────────────────────────────────
version_ge() {
    printf '%s\n%s\n' "$2" "$1" | sort -V -C
}

find_uv() {
    if command -v uv >/dev/null 2>&1; then
        command -v uv
        return
    fi
    for cand in "$HOME/.cargo/bin/uv" "$HOME/.local/bin/uv"; do
        if [ -x "$cand" ]; then
            printf '%s' "$cand"
            return
        fi
    done
}

confirm() {
    local prompt="$1"
    local default="${2:-Y}"
    local choice
    read -r -p "$prompt [$default]: " choice
    choice=${choice:-$default}
    [[ "$choice" =~ ^[Yy]$ ]]
}

section() {
    echo ""
    echo -e "${CYAN}${BOLD}$1${NC}"
}

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}!${NC} $1"; }
err()  { echo -e "  ${RED}✗${NC} $1"; }
info() { echo -e "  ${BLUE}ℹ${NC} $1"; }

# ── banner ─────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║  📦 maru-deep-pro-search 설치를 시작합니다                  ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ── 1. Discover Python ─────────────────────────────────────────
section "1. Python 환경 확인"
PYTHON_CMD=""
PYTHON_VERSION=""
for cmd in python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
        ver=$($cmd -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")' 2>/dev/null || true)
        if [ -n "$ver" ]; then
            PYTHON_CMD="$cmd"
            PYTHON_VERSION="$ver"
            break
        fi
    fi
done

PYTHON_OK=false
if [ -n "$PYTHON_VERSION" ]; then
    if version_ge "$PYTHON_VERSION" "${TARGET_PY}.0"; then
        PYTHON_OK=true
    fi
fi

if [ "$PYTHON_OK" = true ]; then
    ok "Python ${PYTHON_VERSION} 사용 가능"
    info "이 버전으로 설치를 진행합니다."
else
    if [ -n "$PYTHON_VERSION" ]; then
        err "Python ${PYTHON_VERSION} 감지됨 (≥${TARGET_PY} 필요)"
    else
        err "Python을 찾을 수 없음"
    fi
    echo ""
    echo -e "${BOLD}이 프로젝트는 Python ${TARGET_PY} 이상이 필요합니다.${NC}"
    if confirm "uv를 사용해 Python ${TARGET_PY}를 자동 설치하시겠습니까?"; then
        USE_UV=true
    else
        info "수동으로 Python ${TARGET_PY}를 설치한 후 다시 실행해 주세요."
        info "  https://www.python.org/downloads/"
        exit 1
    fi
fi

# ── 2. Discover uv ─────────────────────────────────────────────
UV_BIN=$(find_uv)

if [ "$PYTHON_OK" = true ]; then
    if [ -n "$UV_BIN" ]; then
        ok "uv 감지됨"
        USE_UV=true
    else
        echo ""
        echo "설치 방법을 선택하세요:"
        echo "  1) pip  – 시스템 Python에 직접 설치"
        echo "  2) uv   – 권장. 독립 환경에 설치되며 Python 버전 관리가 쉬움"
        read -r -p "선택 [1/2] (기본: 2): " choice
        choice=${choice:-2}
        if [ "$choice" = "2" ]; then
            USE_UV=true
        fi
    fi
fi

# ── 3. Ensure uv is installed ──────────────────────────────────
if [ "$USE_UV" = true ] && [ -z "$UV_BIN" ]; then
    section "2. uv 설치"
    if confirm "uv가 필요합니다. 지금 설치하시겠습니까?"; then
        echo "   https://astral.sh/uv/install.sh"
        curl -LsSf https://astral.sh/uv/install.sh | sh

        export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
        UV_BIN=$(find_uv)

        if [ -z "$UV_BIN" ]; then
            echo ""
            err "uv 설치에 실패했습니다."
            info "수동으로 실행해 주세요:"
            info "  curl -LsSf https://astral.sh/uv/install.sh | sh"
            exit 1
        fi
        ok "uv 설치 완료  ($UV_BIN)"
    else
        info "uv 설치 후 다시 실행해 주세요."
        info "  https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
fi

# ── 4. Detect existing install ─────────────────────────────────
section "3. 기존 설치 확인"
if command -v maru-deep-pro-search >/dev/null 2>&1; then
    old_ver=$(maru-deep-pro-search --version 2>/dev/null || echo "unknown")
    warn "기존 설치 감지: ${old_ver}"
    info "GitHub 최신 코드로 교체합니다."
else
    info "기존 설치 없음"
fi

# ── 5. Install the package ─────────────────────────────────────
section "4. 패키지 설치"
if [ "$USE_UV" = true ]; then
    info "GitHub 저장소에서 최신 코드를 받습니다..."
    "$UV_BIN" tool install --python "${TARGET_PY}" --reinstall \
        "git+https://github.com/claudianus/maru-deep-pro-search.git"
else
    info "PyPI에서 설치합니다..."
    $PYTHON_CMD -m pip install --user "maru-deep-pro-search"
fi

# Verify
new_ver=$(maru-deep-pro-search --version 2>/dev/null || echo "unknown")
ok "maru-deep-pro-search ${new_ver} 설치 완료"

# ── 5. Hardware detection ──────────────────────────────────────
section "5. 하드웨어 탐지"
info "시스템 사양을 분석합니다..."
# Run Python hardware detection
python3 -c "
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
" 2>/dev/null || warn "하드웨어 탐지 실패 (선택적 기능)"

# GPU wheel selection for llama-cpp-python
if command -v nvidia-smi >/dev/null 2>&1; then
    info "NVIDIA GPU 감지됨 — CUDA 가속 wheel 설치"
    pip install --force-reinstall llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu122
elif [[ "$OSTYPE" == "darwin"* ]]; then
    info "macOS 감지됨 — Metal 가속 wheel 설치"
    pip install --force-reinstall llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/metal
fi

# ── 6. Model download ──────────────────────────────────────────
section "6. 경량 LLM 모델 다운로드"
info "콘텐츠 정제용 경량 모델을 다운로드합니다..."
info "이 모델은 웹 검색 결과를 깔끔하게 정리하여 토큰을 절약합니다."

# Run model download via Python
python3 -c "
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
print(f'Size: {MODEL_REGISTRY[model_name][\"size_mb\"]} MB')
print('Downloading...')

try:
    path = manager.ensure_model(model_name)
    print(f'Model ready: {path}')
except Exception as e:
    print(f'Download failed: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null

if [ $? -eq 0 ]; then
    ok "모델 다운로드 완료"
else
    warn "모델 다운로드 실패 — 런타임에 자동으로 재시도됩니다"
fi

# ── 7. Pre-download embedding model (avoid first deep_research cold start) ──
section "7. 임베딩 모델 사전 다운로드"
info "첫 deep_research 지연 방지 — Hugging Face에서 Granite 임베딩을 받습니다."
if command -v maru-deep-pro-search-setup >/dev/null 2>&1; then
    WARMUP_CMD=(maru-deep-pro-search-setup warmup-embeddings -q)
elif $PYTHON_CMD -c "import maru_deep_pro_search.cli.setup" 2>/dev/null; then
    WARMUP_CMD=("$PYTHON_CMD" -m maru_deep_pro_search.cli.setup warmup-embeddings -q)
else
    WARMUP_CMD=()
fi
if [ "${#WARMUP_CMD[@]}" -gt 0 ] && "${WARMUP_CMD[@]}"; then
    ok "임베딩 모델 준비 완료"
else
    if [ "${#WARMUP_CMD[@]}" -eq 0 ]; then
        warn "warmup CLI 없음 — 패키지 재설치 후 maru-deep-pro-search-setup warmup-embeddings 실행"
    else
        warn "임베딩 모델 다운로드 실패 — 네트워크 확인 후 재실행:"
        info "  maru-deep-pro-search-setup warmup-embeddings"
    fi
fi

# ── 8. Optional setup wizard ───────────────────────────────────
section "8. 설정 마법사"
echo "설정 마법사는 AI 에이전트(Claude, Cursor, Kimi 등)를 자동 감지하고"
echo "MCP 서버를 등록하는 과정입니다."
echo ""
if confirm "지금 설정 마법사를 실행하시겠습니까?"; then
    echo ""
    maru-deep-pro-search setup
else
    info "설정은 나중에 직접 실행할 수 있습니다:"
    info "  maru-deep-pro-search setup"
fi

# ── 9. Summary ─────────────────────────────────────────────────
section "✅ 설치 완료 요약"
ok "Python: ${PYTHON_VERSION:-${TARGET_PY} (via uv)}"
ok "패키지: ${new_ver}"
ok "설치 위치: $(which maru-deep-pro-search)"
echo ""
echo -e "${BOLD}사용 가능한 명령어:${NC}"
echo "  maru-deep-pro-search setup         # 에이전트 설정"
echo "  maru-deep-pro-search setup --list  # 설치된 에이전트 목록"
echo "  maru-deep-pro-search init          # 프로젝트 하네스 초기화"
echo "  maru-deep-pro-search --version     # 버전 확인"
echo ""
