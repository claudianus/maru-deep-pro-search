# Sandbox container for maru-deep-pro-search MCP server
# Recommended for production deployments per MCP security best practices:
# https://www.redhat.com/en/blog/mcp-security-current-situation

FROM python:3.12-slim

LABEL maintainer="maru-deep-pro-search"
LABEL description="Sandboxed MCP search server with zero API keys"

# Security: run as non-root
RUN groupadd -r maru && useradd -r -g maru maru

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy package files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install dependencies
RUN uv pip install --system -e .

# Create cache directories with correct permissions
RUN mkdir -p /app/.maru && chown -R maru:maru /app

USER maru

# Expose SSE transport port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import maru_deep_pro_search; print('ok')" || exit 1

# Default: run MCP server via stdio (for Claude Desktop, Cursor, etc.)
# Override with --transport sse for HTTP endpoint
ENTRYPOINT ["python", "-m", "maru_deep_pro_search.server"]
CMD ["--transport", "stdio"]
