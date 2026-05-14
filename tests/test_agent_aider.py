"""Tests for Aider agent adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from maru_deep_pro_search.cli.agents.aider import AiderAdapter, _detect_quality_tools


class TestDetect:
    def test_detected(self, monkeypatch: Any) -> None:
        monkeypatch.setattr(
            "shutil.which", lambda cmd: "/usr/bin/aider" if cmd == "aider" else None
        )
        assert AiderAdapter().detect() is True

    def test_not_detected(self, monkeypatch: Any) -> None:
        monkeypatch.setattr("shutil.which", lambda _cmd: None)
        assert AiderAdapter().detect() is False


class TestPaths:
    def test_conventions_user(self) -> None:
        p = AiderAdapter()._conventions_path("user")
        assert p.name == "CONVENTIONS.md"
        assert ".aider" in str(p)

    def test_conventions_project(self) -> None:
        p = AiderAdapter()._conventions_path("project")
        assert p == Path("CONVENTIONS.md")

    def test_config_user(self) -> None:
        p = AiderAdapter()._config_path("user")
        assert p.name == ".aider.conf.yml"
        assert ".aider" in str(p)

    def test_config_project(self) -> None:
        p = AiderAdapter()._config_path("project")
        assert p == Path(".aider.conf.yml")

    def test_ignore_user(self) -> None:
        p = AiderAdapter()._ignore_path("user")
        assert p.name == ".aiderignore"
        assert ".aider" in str(p)

    def test_ignore_project(self) -> None:
        p = AiderAdapter()._ignore_path("project")
        assert p == Path(".aiderignore")


class TestBackupRestore:
    def test_backup(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = AiderAdapter()
        monkeypatch.setattr(adapter, "_conventions_path", lambda _s: tmp_path / "conv")
        monkeypatch.setattr(adapter, "_config_path", lambda _s: tmp_path / "cfg")
        monkeypatch.setattr(adapter, "_ignore_path", lambda _s: tmp_path / "ign")

        called = []

        def _fake_backup(p: Path):
            called.append(p.name)
            return tmp_path / f"{p.name}.bak.0"

        monkeypatch.setattr("maru_deep_pro_search.cli.agents.aider.backup_file", _fake_backup)
        backups = adapter.backup()
        assert len(backups) == 3
        assert called == ["conv", "cfg", "ign"]

    def test_backup_skips_none(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = AiderAdapter()
        monkeypatch.setattr(adapter, "_conventions_path", lambda _s: tmp_path / "conv")
        monkeypatch.setattr(adapter, "_config_path", lambda _s: tmp_path / "cfg")
        monkeypatch.setattr(adapter, "_ignore_path", lambda _s: tmp_path / "ign")
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.aider.backup_file",
            lambda _p: None,
        )
        assert adapter.backup() == []

    def test_restore_no_backups(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = AiderAdapter()
        monkeypatch.setattr(adapter, "_conventions_path", lambda _s: tmp_path / "conv")
        monkeypatch.setattr(adapter, "_config_path", lambda _s: tmp_path / "cfg")
        assert adapter.restore() is False

    def test_restore_with_backups(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = AiderAdapter()
        conv = tmp_path / "conv"
        conv.touch()
        bak = tmp_path / "conv.bak.0"
        bak.write_text("backup")
        monkeypatch.setattr(adapter, "_conventions_path", lambda _s: conv)
        monkeypatch.setattr(adapter, "_config_path", lambda _s: tmp_path / "cfg2")

        def _fake_restore(orig: Path, bak_path: Path) -> bool:
            assert bak_path.name == "conv.bak.0"
            return True

        monkeypatch.setattr("maru_deep_pro_search.cli.agents.aider.restore_file", _fake_restore)
        assert adapter.restore() is True


class TestInstallMcp:
    def test_delegates_to_inject_rules(self, monkeypatch: Any) -> None:
        adapter = AiderAdapter()
        called = []

        def _inject(scope: str) -> bool:
            called.append(scope)
            return True

        monkeypatch.setattr(adapter, "inject_rules", _inject)
        assert adapter.install_mcp("project") is True
        assert called == ["project"]


class TestInjectRules:
    def test_inject_rules_user(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = AiderAdapter()
        monkeypatch.setattr(adapter, "_conventions_path", lambda _s: tmp_path / "CONVENTIONS.md")
        monkeypatch.setattr(adapter, "_config_path", lambda _s: tmp_path / ".aider.conf.yml")
        monkeypatch.setattr(adapter, "_ignore_path", lambda _s: tmp_path / ".aiderignore")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        written: dict[str, str] = {}

        def _write(path: Path, content: str) -> None:
            written[path.name] = content

        monkeypatch.setattr("maru_deep_pro_search.cli.agents.aider.write_text_safe", _write)
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.aider.read_text_safe",
            lambda _p: "",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.aider.get_protocol_for_agent",
            lambda _name: "# PROTOCOL",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.aider.inject_protocol",
            lambda _content, _protocol: "# PROTOCOL\n",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.aider._detect_quality_tools",
            lambda _root: {},
        )

        assert adapter.inject_rules("user") is True
        assert "CONVENTIONS.md" in written
        assert ".aider.conf.yml" in written
        assert ".aiderignore" in written

        cfg = written[".aider.conf.yml"]
        assert "read: CONVENTIONS.md" in cfg
        assert "auto-lint: true" in cfg
        assert "architect: true" in cfg
        assert "auto-accept-architect: false" in cfg
        assert "auto-test: true" in cfg
        assert "gitignore: true" in cfg
        assert "lint-cmd:" in cfg
        assert "test-cmd:" in cfg

    def test_inject_rules_project(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = AiderAdapter()
        monkeypatch.setattr(adapter, "_conventions_path", lambda _s: tmp_path / "CONVENTIONS.md")
        monkeypatch.setattr(adapter, "_config_path", lambda _s: tmp_path / ".aider.conf.yml")
        monkeypatch.setattr(adapter, "_ignore_path", lambda _s: tmp_path / ".aiderignore")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        written: dict[str, str] = {}

        def _write(path: Path, content: str) -> None:
            written[path.name] = content

        monkeypatch.setattr("maru_deep_pro_search.cli.agents.aider.write_text_safe", _write)
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.aider.read_text_safe",
            lambda _p: "",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.aider.get_protocol_for_agent",
            lambda _name: "# PROTOCOL",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.aider.inject_protocol",
            lambda _content, _protocol: "# PROTOCOL\n",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.aider._detect_quality_tools",
            lambda _root: {},
        )

        assert adapter.inject_rules("project") is True
        assert ".aider.conf.yml" in written

    def test_inject_rules_idempotent(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = AiderAdapter()
        monkeypatch.setattr(adapter, "_conventions_path", lambda _s: tmp_path / "CONVENTIONS.md")
        monkeypatch.setattr(adapter, "_config_path", lambda _s: tmp_path / ".aider.conf.yml")
        monkeypatch.setattr(adapter, "_ignore_path", lambda _s: tmp_path / ".aiderignore")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        written: dict[str, str] = {}

        def _write(path: Path, content: str) -> None:
            written[path.name] = content

        monkeypatch.setattr("maru_deep_pro_search.cli.agents.aider.write_text_safe", _write)
        # Config already has all the settings
        existing_cfg = (
            "read: CONVENTIONS.md\n"
            "auto-lint: true\n"
            "architect: true\n"
            "auto-accept-architect: false\n"
            "auto-test: true\n"
            "gitignore: true\n"
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.aider.read_text_safe",
            lambda p: existing_cfg if ".aider.conf.yml" in str(p) else "",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.aider.get_protocol_for_agent",
            lambda _name: "# PROTOCOL",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.aider.inject_protocol",
            lambda content, _protocol: content + "# PROTOCOL\n" if content else "# PROTOCOL\n",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.aider._detect_quality_tools",
            lambda _root: {},
        )

        assert adapter.inject_rules("user") is True
        cfg = written[".aider.conf.yml"]
        # Should not duplicate lines
        assert cfg.count("read: CONVENTIONS.md") == 1
        assert cfg.count("auto-lint: true") == 1

    def test_inject_rules_with_tools(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = AiderAdapter()
        monkeypatch.setattr(adapter, "_conventions_path", lambda _s: tmp_path / "CONVENTIONS.md")
        monkeypatch.setattr(adapter, "_config_path", lambda _s: tmp_path / ".aider.conf.yml")
        monkeypatch.setattr(adapter, "_ignore_path", lambda _s: tmp_path / ".aiderignore")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        written: dict[str, str] = {}

        def _write(path: Path, content: str) -> None:
            written[path.name] = content

        monkeypatch.setattr("maru_deep_pro_search.cli.agents.aider.write_text_safe", _write)
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.aider.read_text_safe",
            lambda _p: "",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.aider.get_protocol_for_agent",
            lambda _name: "# PROTOCOL",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.aider.inject_protocol",
            lambda _content, _protocol: "# PROTOCOL\n",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.aider._detect_quality_tools",
            lambda _root: {"python_lint": "ruff check .", "python_test": "pytest"},
        )

        assert adapter.inject_rules("user") is True
        cfg = written[".aider.conf.yml"]
        assert "lint-cmd: python: ruff check ." in cfg
        assert "test-cmd: python: pytest" in cfg


class TestDetectQualityTools:
    def test_python_ruff(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").touch()
        monkeypatch.setattr("shutil.which", lambda cmd: "/bin/ruff" if cmd == "ruff" else None)
        tools = _detect_quality_tools(tmp_path)
        assert tools.get("python_lint") == "ruff check ."

    def test_python_flake8(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").touch()
        monkeypatch.setattr("shutil.which", lambda cmd: "/bin/flake8" if cmd == "flake8" else None)
        tools = _detect_quality_tools(tmp_path)
        assert tools.get("python_lint") == "flake8"

    def test_python_pylint(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "setup.py").touch()
        monkeypatch.setattr("shutil.which", lambda cmd: "/bin/pylint" if cmd == "pylint" else None)
        tools = _detect_quality_tools(tmp_path)
        assert tools.get("python_lint") == "pylint"

    def test_python_pytest(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").touch()
        (tmp_path / "pytest.ini").touch()
        monkeypatch.setattr("shutil.which", lambda cmd: "/bin/pytest" if cmd == "pytest" else None)
        tools = _detect_quality_tools(tmp_path)
        assert tools.get("python_test") == "pytest"

    def test_js_npm(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"scripts": {"lint": "eslint .", "test": "jest"}}')
        tools = _detect_quality_tools(tmp_path)
        assert tools.get("js_lint") == "npm run lint"
        assert tools.get("js_test") == "npm run test"

    def test_js_eslint_fallback(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"scripts": {"eslint": "eslint ."}}')
        tools = _detect_quality_tools(tmp_path)
        assert tools.get("js_lint") == "npm run eslint"

    def test_rust(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "Cargo.toml").touch()
        tools = _detect_quality_tools(tmp_path)
        assert tools.get("rust_lint") == "cargo clippy"
        assert tools.get("rust_test") == "cargo test"

    def test_go(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "go.mod").touch()
        tools = _detect_quality_tools(tmp_path)
        assert tools.get("go_lint") == "go vet ./..."
        assert tools.get("go_test") == "go test ./..."

    def test_java_maven(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "pom.xml").touch()
        monkeypatch.setattr("shutil.which", lambda cmd: "/bin/mvn" if cmd == "mvn" else None)
        tools = _detect_quality_tools(tmp_path)
        assert tools.get("java_test") == "mvn test"
        assert tools.get("java_lint") == "mvn spotbugs:check"

    def test_java_gradle(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "build.gradle").touch()
        monkeypatch.setattr("shutil.which", lambda cmd: "/bin/ktlint" if cmd == "ktlint" else None)
        tools = _detect_quality_tools(tmp_path)
        assert tools.get("java_test") == "./gradlew test"
        assert tools.get("kotlin_lint") == "ktlint"

    def test_cpp_cmake(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "CMakeLists.txt").touch()
        (tmp_path / "Makefile").touch()
        monkeypatch.setattr(
            "shutil.which", lambda cmd: "/bin/cppcheck" if cmd == "cppcheck" else None
        )
        tools = _detect_quality_tools(tmp_path)
        assert tools.get("cpp_lint") == "cppcheck --enable=all ."
        assert tools.get("cpp_test") == "make test"

    def test_c_makefile(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "Makefile").touch()
        tools = _detect_quality_tools(tmp_path)
        assert tools.get("c_test") == "make test"

    def test_csharp(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "test.csproj").touch()
        tools = _detect_quality_tools(tmp_path)
        assert tools.get("csharp_lint") == "dotnet format --verify-no-changes"
        assert tools.get("csharp_test") == "dotnet test"

    def test_ruby(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "Gemfile").touch()
        monkeypatch.setattr(
            "shutil.which", lambda cmd: "/bin/rubocop" if cmd == "rubocop" else None
        )
        tools = _detect_quality_tools(tmp_path)
        assert tools.get("ruby_lint") == "rubocop"

    def test_ruby_rspec(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "Gemfile").touch()
        monkeypatch.setattr("shutil.which", lambda cmd: "/bin/rspec" if cmd == "rspec" else None)
        tools = _detect_quality_tools(tmp_path)
        assert tools.get("ruby_test") == "rspec"

    def test_php(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "composer.json").touch()
        (tmp_path / "phpunit.xml").touch()
        monkeypatch.setattr(
            "shutil.which", lambda cmd: "/bin/phpstan" if cmd == "phpstan" else None
        )
        tools = _detect_quality_tools(tmp_path)
        assert tools.get("php_lint") == "phpstan analyse"
        assert tools.get("php_test") == "vendor/bin/phpunit"

    def test_swift(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "Package.swift").touch()
        tools = _detect_quality_tools(tmp_path)
        assert tools.get("swift_lint") == "swiftlint"
        assert tools.get("swift_test") == "swift test"

    def test_dart(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "pubspec.yaml").touch()
        tools = _detect_quality_tools(tmp_path)
        assert tools.get("dart_lint") == "dart analyze"
        assert tools.get("dart_test") == "dart test"

    def test_scala(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "build.sbt").touch()
        monkeypatch.setattr("shutil.which", lambda cmd: "/bin/sbt" if cmd == "sbt" else None)
        tools = _detect_quality_tools(tmp_path)
        assert tools.get("scala_test") == "sbt test"

    def test_deno(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "deno.json").touch()
        tools = _detect_quality_tools(tmp_path)
        assert tools.get("deno_lint") == "deno lint"
        assert tools.get("deno_test") == "deno test"

    def test_deno_jsonc(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "deno.jsonc").touch()
        tools = _detect_quality_tools(tmp_path)
        assert tools.get("deno_lint") == "deno lint"

    def test_biome(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "biome.json").touch()
        tools = _detect_quality_tools(tmp_path)
        assert tools.get("biome_lint") == "biome check ."

    def test_no_tools(self, monkeypatch: Any, tmp_path: Path) -> None:
        tools = _detect_quality_tools(tmp_path)
        assert tools == {}

    def test_js_package_json_exception(self, monkeypatch: Any, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("not valid json")
        tools = _detect_quality_tools(tmp_path)
        assert "js_lint" not in tools
        assert "js_test" not in tools

    def test_inject_rules_ignore_backup_none(self, monkeypatch: Any, tmp_path: Path) -> None:
        adapter = AiderAdapter()
        monkeypatch.setattr(adapter, "_conventions_path", lambda _s: tmp_path / "CONVENTIONS.md")
        monkeypatch.setattr(adapter, "_config_path", lambda _s: tmp_path / ".aider.conf.yml")
        monkeypatch.setattr(adapter, "_ignore_path", lambda _s: tmp_path / ".aiderignore")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        written: dict[str, str] = {}

        def _write(path: Path, content: str) -> None:
            written[path.name] = content

        monkeypatch.setattr("maru_deep_pro_search.cli.agents.aider.write_text_safe", _write)
        # Ignore file already contains .maru/
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.aider.read_text_safe",
            lambda p: ".maru/\n" if ".aiderignore" in str(p) else "",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.aider.get_protocol_for_agent",
            lambda _name: "# PROTOCOL",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.aider.inject_protocol",
            lambda _content, _protocol: "# PROTOCOL\n",
        )
        monkeypatch.setattr(
            "maru_deep_pro_search.cli.agents.aider._detect_quality_tools",
            lambda _root: {},
        )

        assert adapter.inject_rules("user") is True
        # Ignore should not be rewritten since .maru/ already present
        assert ".aiderignore" not in written
