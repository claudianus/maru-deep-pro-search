#!/bin/bash
# One-click installer for maru-deep-pro-search
# Goals:
#   • Detect the system Python version.
#   • If it is < 3.10, automatically install Python 3.12 via uv.
#   • Install the package so the CLI is available globally.
#   • Run the setup wizard.
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
BOLD='\033[1m'
NC='\033[0m'

# ── helpers ────────────────────────────────────────────────────
version_ge() {
    # returns 0 when $1 >= $2
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

# ── banner ─────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}📦 maru-deep-pro-search 설치를 시작합니다...${NC}"
echo ""

# ── 1. Discover Python ─────────────────────────────────────────
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

# ── 2. Discover uv ─────────────────────────────────────────────
UV_BIN=$(find_uv)

# ── 3. Decide strategy ─────────────────────────────────────────
USE_UV=false

if [ "$PYTHON_OK" = true ]; then
    echo -e "  ${GREEN}✓${NC} Python ${PYTHON_VERSION} 감지됨"
    if [ -n "$UV_BIN" ]; then
        echo -e "  ${GREEN}✓${NC} uv 감지됨"
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
else
    if [ -n "$PYTHON_VERSION" ]; then
        echo -e "  ${RED}✗${NC} Python ${PYTHON_VERSION} 감지됨 (≥${TARGET_PY} 필요)"
    else
        echo -e "  ${RED}✗${NC} Python을 찾을 수 없음"
    fi
    echo ""
    echo -e "${BOLD}이 프로젝트는 Python ${TARGET_PY} 이상이 필요합니다.${NC}"
    echo -e "${YELLOW}→ uv를 사용해 자동으로 해결합니다.${NC}"
    USE_UV=true
fi

# ── 4. Ensure uv is installed ──────────────────────────────────
if [ "$USE_UV" = true ] && [ -z "$UV_BIN" ]; then
    echo ""
    echo -e "${BOLD}→ uv 설치 중...${NC}"
    echo "   https://astral.sh/uv/install.sh"
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Refresh PATH for this shell session
    export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
    UV_BIN=$(find_uv)

    if [ -z "$UV_BIN" ]; then
        echo ""
        echo -e "${RED}❌ uv 설치에 실패했습니다.${NC}"
        echo ""
        echo "수동으로 실행해 주세요:"
        echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo "   # 터미널을 재시작한 후 다시 이 스크립트를 실행하세요"
        exit 1
    fi
    echo -e "  ${GREEN}✓${NC} uv 설치 완료"
fi

# ── 5. Install the package ─────────────────────────────────────
echo ""
if [ "$USE_UV" = true ]; then
    echo -e "${BOLD}→ uv로 설치합니다...${NC}"
    # Install directly from the GitHub repo so users always get the
    # latest fixes without waiting for a PyPI release.
    "$UV_BIN" tool install --python "${TARGET_PY}" --reinstall \
        "git+https://github.com/claudianus/maru-deep-pro-search.git"
else
    echo -e "${BOLD}→ pip로 설치합니다...${NC}"
    $PYTHON_CMD -m pip install --user maru-deep-pro-search
fi

# ── 6. Run setup wizard ────────────────────────────────────────
echo ""
echo -e "${BOLD}🚀 설정 마법사를 실행합니다...${NC}"
echo ""
maru-deep-pro-search setup

# ── 7. Done ────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}✅ 완료!${NC} AI 에이전트가 설정되었습니다."
echo ""
echo "사용 가능한 명령어:"
echo "  maru-deep-pro-search setup        # 에이전트 재설정"
echo "  maru-deep-pro-search setup --list # 설치된 에이전트 목록"
echo ""
