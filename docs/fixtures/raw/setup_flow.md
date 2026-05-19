# CLI: setup check + embedding warmup

```bash
$ maru-deep-pro-search setup --check
```

```text
[32m✓[0m Python 3.14.4 사용 중

🔍 설정 상태 확인 중 (읽기 전용)...

   ✗ Claude Code — MCP ok | protocol ok | WARN stale_hook maru_research_gate.py (unmanaged — run setup --repair) | WARN stale_hook maru_research_revert.py (unmanaged — run setup --repair) | WARN stale_hook maru_session_start.py (unmanaged — run setup --repair)
   ✓ Cursor — MCP ok | protocol ok
   ✗ Kimi Code CLI — MCP ok | protocol ok | WARN stale_hook kimi_research_gate.py (unmanaged — run setup --repair)
   ✓ AntiGravity — MCP ok | protocol ok
   ✓ Kilo Code — MCP ok | protocol ok
   ✓ OpenCode — MCP ok | protocol ok
   ✓ GitHub Copilot — MCP ok | protocol ok
   ✗ Codeium — MCP ok | protocol MISSING | WARN rules_missing
   ✓ Tabnine — MCP ok | protocol ok
   ✓ Hermes (Nous Research) — MCP ok | protocol ok
   ✓ OpenAI Codex — MCP ok | protocol ok

[33m일부 항목에 문제가 있습니다.[0m [1mmaru-deep-pro-search setup --repair[0m 로 자동 수리할 수 있습니다.
```

```bash
$ maru-deep-pro-search warmup-embeddings -q
```

```text
[32m✓[0m Python 3.14.4 사용 중
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.

Loading weights:   0%|          | 0/74 [00:00<?, ?it/s]
Loading weights: 100%|██████████| 74/74 [00:00<00:00, 28083.47it/s]
```
