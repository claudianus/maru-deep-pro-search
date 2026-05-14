"""Tests for config backup and restore utilities."""

from __future__ import annotations

import json

from maru_deep_pro_search.cli.backup import (
    backup_dir,
    backup_file,
    read_json_safe,
    read_text_safe,
    restore_dir,
    restore_file,
    write_json_safe,
    write_text_safe,
)


class TestBackupFile:
    def test_backup_existing_file(self, tmp_path):
        src = tmp_path / "config.json"
        src.write_text('{"key": "value"}')
        bak = backup_file(src)
        assert bak is not None
        assert bak.exists()
        assert bak.name.startswith("config.json.bak.")

    def test_backup_missing_file(self, tmp_path):
        src = tmp_path / "missing.json"
        assert backup_file(src) is None


class TestRestoreFile:
    def test_restore_success(self, tmp_path):
        src = tmp_path / "config.json"
        src.write_text("old")
        bak = tmp_path / "config.json.bak.20240101-120000"
        bak.write_text("restored")
        assert restore_file(src, bak) is True
        assert src.read_text() == "restored"

    def test_restore_missing_backup(self, tmp_path):
        src = tmp_path / "config.json"
        bak = tmp_path / "missing.bak"
        assert restore_file(src, bak) is False


class TestReadJsonSafe:
    def test_missing_file(self, tmp_path):
        assert read_json_safe(tmp_path / "missing.json") == {}

    def test_valid_json(self, tmp_path):
        path = tmp_path / "data.json"
        path.write_text('{"a": 1}')
        assert read_json_safe(path) == {"a": 1}

    def test_invalid_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not json")
        assert read_json_safe(path) == {}

    def test_non_dict_json(self, tmp_path):
        path = tmp_path / "list.json"
        path.write_text("[1, 2, 3]")
        assert read_json_safe(path) == {}


class TestWriteJsonSafe:
    def test_creates_parents(self, tmp_path):
        path = tmp_path / "deep" / "dir" / "data.json"
        write_json_safe(path, {"key": "val"})
        assert path.exists()
        assert json.loads(path.read_text()) == {"key": "val"}


class TestReadTextSafe:
    def test_missing_file(self, tmp_path):
        assert read_text_safe(tmp_path / "missing.txt") == ""

    def test_valid_file(self, tmp_path):
        path = tmp_path / "file.txt"
        path.write_text("hello")
        assert read_text_safe(path) == "hello"


class TestWriteTextSafe:
    def test_creates_parents(self, tmp_path):
        path = tmp_path / "deep" / "dir" / "file.txt"
        write_text_safe(path, "content")
        assert path.read_text() == "content"


class TestBackupDir:
    def test_backup_existing_dir(self, tmp_path):
        src = tmp_path / "mydir"
        src.mkdir()
        (src / "file.txt").write_text("data")
        bak = backup_dir(src)
        assert bak is not None
        assert (bak / "file.txt").exists()

    def test_backup_missing_dir(self, tmp_path):
        assert backup_dir(tmp_path / "missing") is None


class TestRestoreDir:
    def test_restore_success(self, tmp_path):
        src = tmp_path / "mydir"
        src.mkdir()
        (src / "old.txt").write_text("old")
        bak = tmp_path / "mydir.bak.20240101-120000"
        bak.mkdir()
        (bak / "new.txt").write_text("new")
        assert restore_dir(src, bak) is True
        assert not (src / "old.txt").exists()
        assert (src / "new.txt").read_text() == "new"

    def test_restore_missing_backup(self, tmp_path):
        src = tmp_path / "mydir"
        src.mkdir()
        assert restore_dir(src, tmp_path / "missing") is False
