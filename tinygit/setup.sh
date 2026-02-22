#!/bin/bash
set -e

GIT_USER="git"
GIT_HOME="/srv/git"
REPOS_DIR="$GIT_HOME/repos"

echo "=== TinyGit Server Setup ==="
echo ""

# Create git user if it doesn't exist
if ! id "$GIT_USER" &>/dev/null; then
    echo "Creating system user '$GIT_USER'..."
    sudo useradd -r -m -d "$GIT_HOME" -s /usr/bin/git-shell "$GIT_USER"
    echo "Created user '$GIT_USER' with home $GIT_HOME"
else
    echo "User '$GIT_USER' already exists."
fi

# Set up SSH directory
SSH_DIR="$GIT_HOME/.ssh"
AUTH_KEYS="$SSH_DIR/authorized_keys"

sudo mkdir -p "$SSH_DIR"
sudo touch "$AUTH_KEYS"
sudo chmod 700 "$SSH_DIR"
sudo chmod 600 "$AUTH_KEYS"
sudo chown -R "$GIT_USER:$GIT_USER" "$SSH_DIR"

# Add SSH key if provided
if [ -n "$1" ]; then
    echo "Adding provided SSH key..."
    echo "$1" | sudo tee -a "$AUTH_KEYS" > /dev/null
    echo "Key added."
elif [ -t 0 ]; then
    echo ""
    echo "Paste an SSH public key to authorize (or press Enter to skip):"
    read -r SSH_KEY
    if [ -n "$SSH_KEY" ]; then
        echo "$SSH_KEY" | sudo tee -a "$AUTH_KEYS" > /dev/null
        echo "Key added."
    else
        echo "Skipped. Add keys later to $AUTH_KEYS"
    fi
fi

# Create repos directory
sudo mkdir -p "$REPOS_DIR"
sudo chown "$GIT_USER:$GIT_USER" "$REPOS_DIR"
echo "Repos directory: $REPOS_DIR"

# Install Python dependencies
if [ -f "requirements.txt" ]; then
    echo ""
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Usage:"
echo "  Create a repo:    tinygit create <name> \"<description>\""
echo "  List repos:       tinygit list"
echo "  Delete a repo:    tinygit delete <name>"
echo "  Clone a repo:     git clone git@$(hostname):repos/<name>.git"
echo "  Add remote:       git remote add origin git@$(hostname):repos/<name>.git"
echo "  Start web UI:     tinygit serve"
echo ""
echo "Or manage remotely from your local machine:"
echo "  tinygit remote set user@$(hostname)"
echo "  tinygit list"
echo ""
