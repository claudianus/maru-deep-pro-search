"""Generate CI/CD workflow templates for automated research."""

from __future__ import annotations

import argparse
from pathlib import Path

from .env_check import bold, green, yellow

_GITHUB_WORKFLOW_TEMPLATE = """name: Maru Deep Research

on:
  pull_request:
    types: [opened, synchronize]
  issues:
    types: [opened]
  workflow_dispatch:
    inputs:
      query:
        description: "Research query"
        required: true
        default: "latest security best practices"

jobs:
  research:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install maru-deep-pro-search
        run: |
          pip install git+https://github.com/marudev/maru-deep-pro-search.git

      - name: Run deep research
        env:
          MARU_QUERY: ${{ github.event.inputs.query || github.event.pull_request.title }}
        run: |
          python -m maru_deep_pro_search.server research "$MARU_QUERY" --output research-report.md

      - name: Upload research report
        uses: actions/upload-artifact@v4
        with:
          name: research-report
          path: research-report.md
"""


def cmd_generate_workflow(args: argparse.Namespace) -> int:
    """Generate a GitHub Actions workflow file for automated research."""
    path = Path(".github/workflows/maru-research.yml")
    if path.exists() and not args.force:
        print(yellow(f"⚠ Workflow already exists at {path}"))
        print("   Use --force to overwrite")
        return 1

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_GITHUB_WORKFLOW_TEMPLATE, encoding="utf-8")
    print(green(f"✓ Generated workflow: {path}"))
    print(f"  {bold('Trigger:')} PR open/sync, issue open, or manual dispatch")
    print(f"  {bold('Install:')} pip install git+https://github.com/marudev/maru-deep-pro-search.git")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="maru-deep-pro-search workflow",
        description="Generate CI/CD workflow templates for automated research pipelines.",
        epilog="Example: maru-deep-pro-search workflow --force",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing workflow file if it exists",
    )
    args = parser.parse_args(argv)
    return cmd_generate_workflow(args)
