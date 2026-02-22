"""SSH execution and config persistence for remote TinyGit management."""

import json
import os
import subprocess
import sys


def get_config_path():
    """Return path to ~/.config/tinygit/config.json."""
    return os.path.join(os.path.expanduser("~"), ".config", "tinygit", "config.json")


def load_config():
    """Read config from disk. Returns empty dict if file doesn't exist."""
    path = get_config_path()
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def save_config(cfg):
    """Write config dict to disk, creating parent dirs as needed."""
    path = get_config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")


def get_remote():
    """Return configured remote string (e.g. 'user@host') or None."""
    cfg = load_config()
    return cfg.get("remote")


def get_repos_dir():
    """Return configured remote repos_dir or None."""
    cfg = load_config()
    return cfg.get("repos_dir")


def ssh_run(remote, command):
    """Run a command on the remote via SSH, streaming stdout/stderr.

    Returns the exit code of the remote process.
    """
    proc = subprocess.Popen(
        ["ssh", remote, command],
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    proc.wait()
    return proc.returncode
