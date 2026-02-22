#!/usr/bin/env bash
# =============================================================
# setup.sh — Runs once after container creation
# =============================================================

set -euo pipefail

echo "============================================="
echo "  Claude Code Sandbox — first-time setup"
echo "============================================="

# Ensure Claude config directory exists
mkdir -p "$HOME/.claude"

# Verify Claude Code is installed
if command -v claude &>/dev/null; then
    echo "[ok] Claude Code installed: $(claude --version 2>/dev/null || echo 'unknown version')"
else
    echo "[!!] Claude Code not found, installing..."
    npm install -g @anthropic-ai/claude-code
fi

# Verify git is configured
if git config user.name &>/dev/null; then
    echo "[ok] Git user: $(git config user.name)"
else
    echo "[!!] Git user.name not set. Your host ~/.gitconfig should be mounted."
    echo "     Set it with: git config --global user.name 'Your Name'"
fi

# Check for API key
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    echo "[ok] ANTHROPIC_API_KEY is set"
else
    echo "[--] ANTHROPIC_API_KEY not set. You can:"
    echo "     1. Set it on your host: export ANTHROPIC_API_KEY=sk-ant-..."
    echo "     2. Or log in interactively: claude login"
fi

echo ""
echo "============================================="
echo "  Ready. Run 'claude' to start."
echo "============================================="
