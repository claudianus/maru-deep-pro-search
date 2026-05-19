"""CLI to pre-download and warm the local embedding model."""

from __future__ import annotations

import argparse
import importlib.util
import sys

from .env_check import bold, ensure_compatible_python, green, red, yellow
from .setup import _pip_install_sentence_transformers


def cmd_warmup_embeddings(args: argparse.Namespace) -> int:
    """Download and load the configured embedding model (install-time prefetch)."""
    if not importlib.util.find_spec("sentence_transformers"):
        print(f"{yellow('!')} sentence-transformers 미설치 — 설치 중...")
        ok, detail = _pip_install_sentence_transformers()
        if not ok:
            print(red("✗ sentence-transformers 설치 실패"))
            if detail:
                print(detail)
            return 1
        print(green(f"✓ sentence-transformers 설치 완료 ({detail})"))

    from ..embeddings import DEFAULT_EMBEDDING_MODEL, embedding_model_name, warmup_embeddings

    model = embedding_model_name() or DEFAULT_EMBEDDING_MODEL
    if not args.quiet:
        print(f"\n{bold('⬇️  임베딩 모델 사전 다운로드')}")
        print(f"   모델: {model}")
        print("   Hugging Face에서 가져오며 1–3분 걸릴 수 있습니다...\n")

    try:
        warmed = warmup_embeddings()
    except Exception as exc:
        print(red(f"✗ 임베딩 모델 준비 실패: {exc}"))
        print("  네트워크·Hugging Face 접근·디스크 공간을 확인하세요.")
        return 1

    if not args.quiet:
        print(green(f"✓ 임베딩 모델 준비 완료 ({warmed})"))
        print("  첫 deep_research 시 추가 다운로드 없이 시맨틱 랭킹이 동작합니다.\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="maru-deep-pro-search-setup warmup-embeddings",
        description="Pre-download and warm the local semantic embedding model.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Only print errors",
    )
    args = parser.parse_args(argv)
    if ensure_compatible_python() != 0:
        return 1
    return cmd_warmup_embeddings(args)


if __name__ == "__main__":
    sys.exit(main())
