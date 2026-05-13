"""Tests for token default changes."""

import inspect

from maru_deep_pro_search.tools import (
    TOOLS,
    tool_fetch_bulk,
    tool_fetch_page,
    tool_stealthy_fetch,
)


class TestTokenDefaults:
    def test_fetch_page_default_increased(self):
        sig = inspect.signature(tool_fetch_page)
        default = sig.parameters["max_tokens"].default
        assert default == 6000, f"Expected 6000, got {default}"

    def test_fetch_bulk_default_increased(self):
        sig = inspect.signature(tool_fetch_bulk)
        default = sig.parameters["max_tokens"].default
        assert default == 3000, f"Expected 3000, got {default}"

    def test_stealthy_fetch_default_increased(self):
        sig = inspect.signature(tool_stealthy_fetch)
        default = sig.parameters["max_tokens"].default
        assert default == 6000, f"Expected 6000, got {default}"

    def test_maximum_bounds_unchanged(self):
        schema = TOOLS["fetch_page"][2]["properties"]["max_tokens"]
        assert schema["maximum"] == 8000
        schema = TOOLS["fetch_bulk"][2]["properties"]["max_tokens"]
        assert schema["maximum"] == 5000

    def test_tool_registry_defaults_updated(self):
        assert TOOLS["fetch_page"][2]["properties"]["max_tokens"]["default"] == 6000
        assert TOOLS["fetch_bulk"][2]["properties"]["max_tokens"]["default"] == 3000
        assert TOOLS["stealthy_fetch"][2]["properties"]["max_tokens"]["default"] == 6000
