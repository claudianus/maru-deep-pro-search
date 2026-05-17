"""Aider adapter — terminal-first AI coding agent with deep git integration."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..backup import (
    backup_file,
    read_text_safe,
    restore_file,
    sorted_backup_paths,
    write_text_safe,
)
from ..hooks_templates import template_body, write_managed_hook
from ..idempotent import lines_contain
from ..prompts import get_protocol_for_agent, inject_protocol
from .base import AgentAdapter


def _detect_quality_tools(root: Path = Path(".")) -> dict[str, str]:
    """Auto-detect lint/test commands based on project files."""
    tools: dict[str, str] = {}

    # Python
    if (root / "pyproject.toml").exists() or (root / "setup.py").exists():
        if shutil.which("ruff"):
            tools["python_lint"] = "ruff check ."
        elif shutil.which("flake8"):
            tools["python_lint"] = "flake8"
        elif shutil.which("pylint"):
            tools["python_lint"] = "pylint"

    # JavaScript / TypeScript
    if (root / "package.json").exists():
        pkg = root / "package.json"
        try:
            import json

            scripts = json.loads(pkg.read_text()).get("scripts", {})
            if "lint" in scripts:
                tools["js_lint"] = "npm run lint"
            elif "eslint" in scripts:
                tools["js_lint"] = "npm run eslint"
            if "test" in scripts:
                tools["js_test"] = "npm run test"
        except Exception:
            pass

    # Rust
    if (root / "Cargo.toml").exists():
        tools["rust_lint"] = "cargo clippy"
        tools["rust_test"] = "cargo test"

    # Go
    if (root / "go.mod").exists():
        tools["go_lint"] = "go vet ./..."
        tools["go_test"] = "go test ./..."

    # Java / Kotlin
    if (root / "pom.xml").exists():
        tools["java_test"] = "mvn test"
        if shutil.which("mvn"):
            tools["java_lint"] = "mvn spotbugs:check"
    elif (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        tools["java_test"] = "./gradlew test"
        if shutil.which("ktlint"):
            tools["kotlin_lint"] = "ktlint"

    # C / C++
    if (root / "CMakeLists.txt").exists():
        if shutil.which("cppcheck"):
            tools["cpp_lint"] = "cppcheck --enable=all ."
        if (root / "Makefile").exists():
            tools["cpp_test"] = "make test"
    elif (root / "Makefile").exists():
        tools["c_test"] = "make test"

    # C# (.NET)
    if any(root.glob("*.csproj")):
        tools["csharp_lint"] = "dotnet format --verify-no-changes"
        tools["csharp_test"] = "dotnet test"

    # Ruby
    if (root / "Gemfile").exists():
        if shutil.which("rubocop"):
            tools["ruby_lint"] = "rubocop"
        if shutil.which("rspec"):
            tools["ruby_test"] = "rspec"

    # PHP
    if (root / "composer.json").exists():
        if shutil.which("phpstan"):
            tools["php_lint"] = "phpstan analyse"
        if (root / "phpunit.xml").exists() or (root / "phpunit.xml.dist").exists():
            tools["php_test"] = "vendor/bin/phpunit"

    # Swift
    if (root / "Package.swift").exists():
        tools["swift_lint"] = "swiftlint"
        tools["swift_test"] = "swift test"

    # Dart / Flutter
    if (root / "pubspec.yaml").exists():
        tools["dart_lint"] = "dart analyze"
        tools["dart_test"] = "dart test"

    # Scala
    if (root / "build.sbt").exists() and shutil.which("sbt"):
        tools["scala_test"] = "sbt test"

    # TypeScript (Deno, Biome)
    if (root / "deno.json").exists() or (root / "deno.jsonc").exists():
        tools["deno_lint"] = "deno lint"
        tools["deno_test"] = "deno test"
    if (root / "biome.json").exists():
        tools["biome_lint"] = "biome check ."

    return tools


class AiderAdapter(AgentAdapter):
    name = "aider"
    display_name = "Aider"

    def detect(self) -> bool:
        return shutil.which("aider") is not None

    # ── paths ────────────────────────────────────────────────────
    def _conventions_path(self, scope: str) -> Path:
        if scope == "project":
            return Path("CONVENTIONS.md")
        return Path.home() / ".aider" / "CONVENTIONS.md"

    def _config_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".aider.conf.yml")
        return Path.home() / ".aider.conf.yml"

    def _ignore_path(self, scope: str) -> Path:
        if scope == "project":
            return Path(".aiderignore")
        return Path.home() / ".aiderignore"

    # ── backup ───────────────────────────────────────────────────
    def backup(self) -> list[Path]:
        paths = [
            self._conventions_path("user"),
            self._config_path("user"),
            self._ignore_path("user"),
        ]
        backups = [backup_file(p) for p in paths]
        return [b for b in backups if b is not None]

    def restore(self) -> bool:
        restored = False
        for p in [
            self._conventions_path("user"),
            self._config_path("user"),
        ]:
            backups = sorted_backup_paths(p)
            if backups:
                restored = restore_file(p, backups[0]) or restored
        return restored

    # ── install MCP (Aider doesn't use MCP natively, but we register via conventions) ──
    def install_mcp(self, scope: str = "user") -> bool:
        return self.inject_rules(scope)

    def refresh_managed_hooks(self, *, repair: bool = False) -> bool:
        gate_script = Path.home() / ".maru" / "aider_research_gate.py"
        write_managed_hook(gate_script, template_body("aider_research_gate"), force=repair)
        return True

    # ── inject rules ─────────────────────────────────────────────
    def inject_rules(self, scope: str = "user", *, repair: bool = False) -> bool:
        root = Path(".") if scope == "project" else Path.home()

        # 1. CONVENTIONS.md
        conv_path = self._conventions_path(scope)
        protocol = get_protocol_for_agent(self.name)

        content = read_text_safe(conv_path)
        new_content = inject_protocol(content, protocol)
        if new_content != content:
            write_text_safe(conv_path, new_content)

        # 2. .aider.conf.yml — with auto-detected quality gates
        config_path = self._config_path(scope)
        raw = read_text_safe(config_path)
        lines = raw.splitlines() if raw else []

        # Ensure read: CONVENTIONS.md
        has_read = any("CONVENTIONS.md" in line for line in lines)
        if not has_read:
            lines.append("read: CONVENTIONS.md")

        # Ensure auto-lint
        has_auto_lint = any(line.strip().startswith("auto-lint:") for line in lines)
        if not has_auto_lint:
            lines.append("auto-lint: true")

        # Enable architect mode (design-then-edit separation)
        has_architect = any(line.strip().startswith("architect:") for line in lines)
        if not has_architect:
            lines.append("architect: true")

        # Disable auto-accept so research gate can intercept
        has_auto_accept = any(line.strip().startswith("auto-accept-architect:") for line in lines)
        if not has_auto_accept:
            lines.append("auto-accept-architect: false")

        # ── RESEARCH GATE: inject research verification into lint-cmd ──
        # Aider runs lint-cmd before accepting edits. We insert a gate
        # script that fails (exit 1) if research hasn't been completed
        # in this session, effectively blocking un-researched edits.
        gate_script = Path.home() / ".maru" / "aider_research_gate.py"
        write_managed_hook(gate_script, template_body("aider_research_gate"), force=repair)

        # Insert research gate as FIRST lint-cmd AND test-cmd
        gate_cmd = f"python: python {gate_script}"
        if not lines_contain(lines, gate_cmd):
            lines.append(f"lint-cmd: {gate_cmd}")
            lines.append(f"test-cmd: {gate_cmd}")

        # Auto-detect and inject lint/test commands
        tools = _detect_quality_tools(root)
        lint_cmds: list[str] = []
        test_cmds: list[str] = []

        for key, cmd in tools.items():
            if "_lint" in key:
                lang = key.replace("_lint", "")
                lint_cmds.append(f"{lang}: {cmd}")
            if "_test" in key:
                lang = key.replace("_test", "")
                test_cmds.append(f"{lang}: {cmd}")

        # Only add if not already present
        for lc in lint_cmds:
            if not lines_contain(lines, lc):
                lines.append(f"lint-cmd: {lc}")
        for tc in test_cmds:
            if not lines_contain(lines, tc):
                lines.append(f"test-cmd: {tc}")

        # Enable auto-test so the test gate (with research check) runs after edits
        has_auto_test = any(line.strip().startswith("auto-test:") for line in lines)
        if not has_auto_test:
            lines.append("auto-test: true")

        # Ensure gitignore behavior
        has_gitignore = any("gitignore" in line for line in lines)
        if not has_gitignore:
            lines.append("gitignore: true")

        write_text_safe(config_path, "\n".join(lines) + "\n")

        # 3. .aiderignore — exclude harness artifacts
        ignore_path = self._ignore_path(scope)
        ignore_content = read_text_safe(ignore_path)
        maru_ignore = (
            "# maru harness\n.maru/knowledge.db\n.maru/knowledge.db-journal\n.maru/*.bak\n"
        )
        if ".maru/" not in ignore_content:
            write_text_safe(ignore_path, ignore_content + "\n" + maru_ignore)

        return True
