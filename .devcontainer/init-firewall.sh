#!/usr/bin/env bash
# =============================================================
# init-firewall.sh — Restrict container network to essentials
#
# Whitelists only the domains Claude Code needs.
# Everything else is blocked by default.
# =============================================================

set -euo pipefail

# Skip if iptables isn't available (e.g., rootless containers)
if ! command -v iptables &>/dev/null; then
    echo "[firewall] iptables not found, skipping firewall setup"
    exit 0
fi

# Skip if we don't have permissions
if ! sudo iptables -L -n &>/dev/null 2>&1; then
    echo "[firewall] insufficient permissions, skipping firewall setup"
    exit 0
fi

echo "[firewall] Setting up network restrictions..."

# Flush existing rules
sudo iptables -F OUTPUT 2>/dev/null || true

# Allow loopback
sudo iptables -A OUTPUT -o lo -j ACCEPT

# Allow established connections
sudo iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow DNS (needed for domain resolution)
sudo iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT

# Allow SSH (for git operations)
sudo iptables -A OUTPUT -p tcp --dport 22 -j ACCEPT

# =============================================================
# Whitelisted domains — resolve and allow
# Add or remove domains as needed for your workflow
# =============================================================
ALLOWED_DOMAINS=(
    # Claude API
    "api.anthropic.com"
    "sentry.io"
    "statsig.anthropic.com"

    # npm registry
    "registry.npmjs.org"

    # GitHub (for git clone/push/pull and packages)
    "github.com"
    "api.github.com"
    "raw.githubusercontent.com"
    "objects.githubusercontent.com"

    # PyPI (for pip install)
    "pypi.org"
    "files.pythonhosted.org"

    # Go modules
    "proxy.golang.org"
    "sum.golang.org"

    # Common CDNs (for downloading tools)
    "deb.nodesource.com"
    "dl.google.com"
)

for domain in "${ALLOWED_DOMAINS[@]}"; do
    # Resolve domain to IPs and whitelist each
    ips=$(dig +short "$domain" 2>/dev/null | grep -E '^[0-9]+\.' || true)
    for ip in $ips; do
        sudo iptables -A OUTPUT -d "$ip" -j ACCEPT 2>/dev/null || true
    done
done

# =============================================================
# Default deny — block everything else
# =============================================================
sudo iptables -A OUTPUT -j DROP

echo "[firewall] Network restrictions active. Only whitelisted domains allowed."
echo "[firewall] Allowed: Claude API, npm, GitHub, PyPI, Go modules, SSH"
