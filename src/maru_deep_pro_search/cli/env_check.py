"""Python environment validation and automatic setup helpers.

Guarantees that the user never gets a cryptic pip error due to an
out-of-date Python interpreter.  Instead we detect the problem early,
explain it, and—whenever possible—fix it automatically via uv.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

MIN_PY_MAJOR = 3
MIN_PY_MINOR = 10


def _color(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m"


def bold(text: str) -> str:
    return _color("1", text)


def red(text: str) -> str:
    return _color("31", text)


def green(text: str) -> str:
    return _color("32", text)


def yellow(text: str) -> str:
    return _color("33", text)


def blue(text: str) -> str:
    return _color("34", text)


def cyan(text: str) -> str:
    return _color("36", text)


def current_python_version() -> tuple[int, int, int]:
    """Return (major, minor, micro) of the running interpreter."""
    return sys.version_info[:3]


def is_python_compatible(major: int = MIN_PY_MAJOR, minor: int = MIN_PY_MINOR) -> bool:
    """Check whether *this* interpreter meets the minimum version."""
    v = sys.version_info
    return v.major > major or (v.major == major and v.minor >= minor)


def find_uv() -> str | None:
    """Return the absolute path to the uv binary, or None."""
    uv = shutil.which("uv")
    if uv:
        return uv
    # Common fallback paths when uv was just installed in the same shell session
    for candidate in (
        "~/.cargo/bin/uv",
        "~/.local/bin/uv",
    ):
        p = shutil.which(candidate)
        if p:
            return p
    return None


def has_pyenv() -> bool:
    return shutil.which("pyenv") is not None


def install_uv() -> str | None:
    """Attempt to install uv via the official installer.

    Returns the path to the uv binary on success, None on failure.
    """
    # macOS / Linux only – Windows users should use install.ps1
    try:
        result = subprocess.run(
            ["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            return None
    except Exception:
        return None

    # Try to locate the newly-installed binary
    for candidate in (
        shutil.which("uv"),
        shutil.which("~/.cargo/bin/uv"),
        shutil.which("~/.local/bin/uv"),
    ):
        if candidate:
            return candidate
    return None


def install_python_via_uv(uv_bin: str, version: str = "3.12") -> bool:
    """Use uv to download and install a specific CPython version."""
    try:
        subprocess.run(
            [uv_bin, "python", "install", version],
            check=True,
            timeout=300,
        )
        return True
    except Exception:
        return False


def print_environment_report() -> None:
    """Print a concise report of the current Python / uv situation."""
    v = current_python_version()
    v_str = f"{v[0]}.{v[1]}.{v[2]}"
    print()
    print(bold("🔍 환경 점검"))
    print()

    if is_python_compatible():
        print(f"  {green('✓')} Python {v_str}")
    else:
        print(f"  {red('✗')} Python {v_str}  (≥{MIN_PY_MAJOR}.{MIN_PY_MINOR} 필요)")

    uv = find_uv()
    if uv:
        print(f"  {green('✓')} uv  ({uv})")
    else:
        print(f"  {yellow('!')} uv 미설치")

    if has_pyenv():
        print(f"  {green('✓')} pyenv 감지됨")
    print()


def ensure_compatible_python() -> int:
    """Entry-point used by the install scripts and setup CLI.

    Returns 0 when everything is fine (or was fixed automatically).
    Returns 1 when the user must act manually.
    """
    if is_python_compatible():
        v = current_python_version()
        print(f"  {green('✓')} Python {v[0]}.{v[1]}.{v[2]} 사용 중")
        return 0

    # Incompatible interpreter – try to recover automatically with uv
    print()
    print(
        red(f"❌  현재 Python {'.'.join(map(str, current_python_version()))}는 지원되지 않습니다.")
    )
    print(red(f"   maru-deep-pro-search에는 Python ≥{MIN_PY_MAJOR}.{MIN_PY_MINOR}가 필요합니다."))
    print()

    uv = find_uv()
    if uv is None:
        print(bold("→ uv를 자동 설치합니다..."))
        print("   https://astral.sh/uv/install.sh")
        uv = install_uv()
        if uv is None:
            print()
            print(red("❌ uv 자동 설치에 실패했습니다."))
            print()
            print(bold("수동으로 다음 명령을 실행해 주세요:"))
            print("   curl -LsSf https://astral.sh/uv/install.sh | sh")
            print()
            print(bold("또는 pyenv를 사용하세요:"))
            print("   pyenv install 3.12 && pyenv global 3.12")
            print()
            return 1
        print(green("   ✓ uv 설치 완료"))
    else:
        print(blue(f"→ uv 감지됨 ({uv})"))

    print()
    print(bold(f"→ uv로 Python {MIN_PY_MAJOR}.{MIN_PY_MINOR}를 설치합니다..."))
    if install_python_via_uv(uv, f"{MIN_PY_MAJOR}.{MIN_PY_MINOR}"):
        print(green(f"   ✓ Python {MIN_PY_MAJOR}.{MIN_PY_MINOR} 설치 완료"))
    else:
        print(red(f"   ✗ Python {MIN_PY_MAJOR}.{MIN_PY_MINOR} 설치 실패"))
        print()
        print(bold("수동으로 설치해 주세요:"))
        print(f"   {uv} python install {MIN_PY_MAJOR}.{MIN_PY_MINOR}")
        return 1

    print()
    print(yellow("! 시스템 Python이 여전히 오래된 버전입니다. 아래 명령으로 설치를 진행하세요:\n"))
    print(bold(f"   {uv} tool install --python {MIN_PY_MAJOR}.{MIN_PY_MINOR} maru-deep-pro-search"))
    print()
    return 1
