FROM ubuntu:24.04

ARG USERNAME=dev
ARG USER_UID=1000
ARG USER_GID=$USER_UID

ENV DEBIAN_FRONTEND=noninteractive

# =============================================================
# System packages — add or remove what you need
# =============================================================
RUN apt-get update && apt-get install -y \
    # Essentials
    git curl wget sudo ca-certificates gnupg \
    # Build tools
    build-essential pkg-config libssl-dev \
    # Useful CLI tools
    vim nano htop tree jq unzip zip ripgrep fd-find \
    # Network tools (for firewall script)
    iptables dnsutils iputils-ping \
    # Python
    python3 python3-pip python3-venv \
    # Misc
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# =============================================================
# Node.js 20 via NodeSource
# =============================================================
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# =============================================================
# Go (latest stable) — remove this block if you don't need Go
# =============================================================
RUN curl -fsSL https://go.dev/dl/go1.23.6.linux-amd64.tar.gz | tar -C /usr/local -xz
ENV PATH="/usr/local/go/bin:$PATH"

# =============================================================
# Rust via rustup — remove this block if you don't need Rust
# =============================================================
# Uncomment if needed:
# RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
# ENV PATH="/root/.cargo/bin:$PATH"

# =============================================================
# Create non-root user
# Ubuntu 24.04 already has a 'ubuntu' user at UID/GID 1000,
# so we remove it first, then create our own.
# =============================================================
RUN userdel -r ubuntu 2>/dev/null || true \
    && groupadd --gid $USER_GID $USERNAME 2>/dev/null || true \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# =============================================================
# Persistent directories
# =============================================================
RUN mkdir -p /commandhistory \
    && touch /commandhistory/.bash_history \
    && chown -R $USERNAME:$USERNAME /commandhistory

RUN mkdir -p /home/$USERNAME/.claude \
    && chown -R $USERNAME:$USERNAME /home/$USERNAME/.claude

# =============================================================
# Copy helper scripts
# =============================================================
COPY init-firewall.sh /usr/local/bin/init-firewall.sh
COPY setup.sh /usr/local/bin/setup.sh
RUN chmod +x /usr/local/bin/init-firewall.sh /usr/local/bin/setup.sh

# =============================================================
# Install Claude Code globally (as root, before user switch)
# =============================================================
RUN npm install -g @anthropic-ai/claude-code

# =============================================================
# Switch to non-root user
# =============================================================
USER $USERNAME
WORKDIR /workspace
