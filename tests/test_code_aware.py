"""Tests for code-aware content analysis."""

from maru_deep_pro_search.extraction.code import (
    analyze_code_content,
    detect_language,
    extract_api_signatures,
)


class TestDetectLanguage:
    def test_detect_python(self):
        code = "def hello():\n    print('world')\n    return 42"
        assert detect_language(code) == "python"

    def test_detect_python_async(self):
        code = "async def fetch(url):\n    async with aiohttp.ClientSession() as s:\n        await s.get(url)"
        assert detect_language(code) == "python"

    def test_detect_javascript(self):
        code = "const x = () => { return fetch('/api').then(r => r.json()) }"
        assert detect_language(code) == "javascript"

    def test_detect_typescript(self):
        code = "interface User { name: string; age: number }\nconst u: User = { name: 'a', age: 1 }"
        assert detect_language(code) == "typescript"

    def test_detect_go(self):
        code = 'func Hello(name string) string {\n    return fmt.Sprintf("hello %s", name)\n}'
        assert detect_language(code) == "go"

    def test_detect_rust(self):
        code = 'pub fn main() {\n    let x = Some(42);\n    println!("{:?}", x.unwrap());\n}'
        assert detect_language(code) == "rust"

    def test_detect_java(self):
        code = 'public class Hello {\n    public static void main(String[] args) {\n        System.out.println("hi");\n    }\n}'
        assert detect_language(code) == "java"

    def test_detect_shell(self):
        code = "$ npm install react\n$ git clone https://github.com/foo/bar.git"
        assert detect_language(code) == "shell"

    def test_detect_sql(self):
        code = "SELECT * FROM users WHERE age > 18 JOIN orders ON users.id = orders.user_id"
        assert detect_language(code) == "sql"

    def test_detect_json(self):
        code = '{"name": "test", "values": [1, 2, 3]}'
        assert detect_language(code) == "json"

    def test_detect_yaml(self):
        code = "name: test\nversion: 1.0\ndependencies:\n  - requests"
        assert detect_language(code) == "yaml"

    def test_detect_html(self):
        code = "<!DOCTYPE html>\n<html>\n<head><title>Test</title></head>\n<body><div>hi</div></body>\n</html>"
        assert detect_language(code) == "html"

    def test_detect_empty(self):
        assert detect_language("") == "text"

    def test_detect_short(self):
        assert detect_language("x = 1") == "text"  # too short to classify


SAMPLE_MARKDOWN = """
# My Python Module

```python
def hello(name: str) -> str:
    return f"Hello {name}"

async def fetch_data(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()

class DataStore:
    def __init__(self, path: str):
        self.path = path

    async def load(self) -> list:
        ...
```

Some text here.

```shell
$ pip install mypackage
```
"""


class TestExtractApiSignatures:
    def test_extract_function_defs(self):
        sigs = extract_api_signatures(SAMPLE_MARKDOWN)
        assert len(sigs) > 0
        names = [s["name"] for s in sigs]
        assert "hello" in names
        assert "fetch_data" in names

    def test_extract_python_specific(self):
        sigs = extract_api_signatures(SAMPLE_MARKDOWN)
        python_sigs = [s for s in sigs if s["language"] == "python"]
        assert any("def hello" in s["signature"] for s in python_sigs)
        assert any("class DataStore" in s["signature"] for s in python_sigs)

    def test_extract_no_code(self):
        sigs = extract_api_signatures("Just plain text without any code.")
        assert len(sigs) == 0


class TestAnalyzeCodeContent:
    def test_tutorial_detection(self):
        md = "# Getting Started Tutorial\n\n```python\nprint('hello')\n```\n\n```python\ndef foo():\n    pass\n```"
        stats = analyze_code_content(md)
        assert stats.is_tutorial
        assert not stats.is_api_reference

    def test_api_reference_detection(self):
        md = "# API Reference\n\n```python\ndef foo():\n    pass\n```\n\n```python\nclass Bar:\n    pass\n```\n\n```python\nasync def baz():\n    pass\n```"
        stats = analyze_code_content(md)
        assert stats.is_api_reference
        assert not stats.is_tutorial

    def test_error_solution_detection(self):
        md = "# Fix: ModuleNotFoundError\n\nWhen you get this error, traceback shows...\n\n```python\npip install missing-module\n```"
        stats = analyze_code_content(md)
        assert stats.is_error_solution

    def test_code_languages(self):
        md = "```python\ndef foo(): pass\n```\n```go\nfunc bar() {}\n```\n```python\nclass Baz: pass\n```"
        stats = analyze_code_content(md)
        assert "python" in stats.code_languages
        assert "go" in stats.code_languages

    def test_code_to_text_ratio(self):
        md = "```python\n" + ("x = 1\n" * 50) + "```\n\nSome short text."
        stats = analyze_code_content(md)
        assert stats.code_to_text_ratio > 0.5  # mostly code

    def test_freshness(self):
        stats = analyze_code_content("", published_date="2024-01-15T00:00:00Z")
        assert stats.freshness_days is not None
        assert stats.freshness_days > 365  # more than a year ago

    def test_empty_markdown(self):
        stats = analyze_code_content("")
        assert stats.code_block_count == 0
        assert stats.code_languages == []
        assert stats.code_to_text_ratio == 0.0
