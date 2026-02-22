import os
import subprocess
from pathlib import Path

from tinygit import config


def _run_git(repo_path, *args):
    """Run a git command against a bare repo and return stdout."""
    result = subprocess.run(
        ["git", "-C", str(repo_path)] + list(args),
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _run_git_bytes(repo_path, *args):
    """Run a git command and return raw bytes."""
    result = subprocess.run(
        ["git", "-C", str(repo_path)] + list(args),
        capture_output=True,
        timeout=10,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def get_repos_dir():
    return Path(config.REPOS_DIR)


def list_repos():
    """List all bare repos in the repos directory."""
    repos_dir = get_repos_dir()
    if not repos_dir.is_dir():
        return []
    repos = []
    for entry in repos_dir.iterdir():
        if entry.is_dir() and (entry / "HEAD").is_file():
            name = entry.name
            if name.endswith(".git"):
                name = name[:-4]
            desc = ""
            desc_file = entry / "description"
            if desc_file.is_file():
                desc = desc_file.read_text().strip()
                if desc.startswith("Unnamed repository"):
                    desc = ""
            last_update = _run_git(entry, "log", "-1", "--format=%ci")
            last_update = last_update.strip()[:10] if last_update else ""
            repos.append({
                "name": name,
                "dir_name": entry.name,
                "description": desc,
                "last_update": last_update,
            })
    repos.sort(key=lambda r: r["last_update"], reverse=True)
    return repos


def get_repo_path(name):
    """Resolve repo name to path, checking both name and name.git."""
    repos_dir = get_repos_dir()
    # Sanitize: prevent directory traversal
    if ".." in name or name.startswith("/"):
        return None
    for candidate in [repos_dir / f"{name}.git", repos_dir / name]:
        if candidate.is_dir() and (candidate / "HEAD").is_file():
            # Ensure it's actually inside repos_dir
            try:
                candidate.resolve().relative_to(repos_dir.resolve())
            except ValueError:
                return None
            return candidate
    return None


def get_default_branch(repo_path):
    """Get the default branch (HEAD ref) of a repo."""
    head_file = repo_path / "HEAD"
    if head_file.is_file():
        content = head_file.read_text().strip()
        if content.startswith("ref: refs/heads/"):
            return content[len("ref: refs/heads/"):]
    return "main"


def ls_tree(repo_path, ref, path=""):
    """List entries in a tree at the given ref and path."""
    args = ["ls-tree", ref]
    if path:
        args.append(path)
    output = _run_git(repo_path, *args)
    if output is None:
        return None
    entries = []
    for line in output.strip().split("\n"):
        if not line:
            continue
        # format: <mode> <type> <hash>\t<name>
        meta, name = line.split("\t", 1)
        parts = meta.split()
        entries.append({
            "mode": parts[0],
            "type": parts[1],  # "blob" or "tree"
            "hash": parts[2],
            "name": name,
        })
    # Sort: directories first, then alphabetical
    entries.sort(key=lambda e: (0 if e["type"] == "tree" else 1, e["name"].lower()))
    return entries


def get_blob(repo_path, ref, filepath):
    """Get file contents as bytes."""
    return _run_git_bytes(repo_path, "show", f"{ref}:{filepath}")



def is_binary(data):
    """Check if data is binary by looking for null bytes in first 8KB."""
    return b"\x00" in data[:8192]


def format_size(size_bytes):
    """Format byte size to human readable."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}K"
    else:
        return f"{size_bytes / (1024 * 1024):.1f}M"


def get_log(repo_path, ref="HEAD", skip=0, limit=30):
    """Get commit log entries."""
    fmt = "%H%x00%h%x00%ci%x00%an%x00%s"
    output = _run_git(
        repo_path, "log", f"--format={fmt}", f"--skip={skip}",
        f"--max-count={limit}", ref, "--"
    )
    if output is None:
        return []
    commits = []
    for line in output.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\x00")
        if len(parts) < 5:
            continue
        commits.append({
            "hash": parts[0],
            "short_hash": parts[1],
            "date": parts[2][:10],
            "author": parts[3],
            "subject": parts[4],
        })
    return commits


def get_commit_count(repo_path, ref="HEAD"):
    """Get total number of commits on a ref."""
    output = _run_git(repo_path, "rev-list", "--count", ref)
    if output is None:
        return 0
    return int(output.strip())


def get_commit(repo_path, sha):
    """Get full commit details."""
    fmt = "%H%x00%h%x00%ci%x00%an%x00%ae%x00%P%x00%B"
    output = _run_git(repo_path, "log", "-1", f"--format={fmt}", sha)
    if output is None:
        return None
    parts = output.split("\x00", 6)
    if len(parts) < 7:
        return None
    parents = parts[5].strip().split() if parts[5].strip() else []
    return {
        "hash": parts[0],
        "short_hash": parts[1],
        "date": parts[2],
        "author": parts[3],
        "email": parts[4],
        "parents": parents,
        "parent_short": parents[0][:7] if parents else None,
        "message": parts[6].strip(),
    }


def get_diff(repo_path, sha):
    """Get the diff for a commit."""
    # Check if this is a root commit (no parents)
    commit = get_commit(repo_path, sha)
    if commit is None:
        return None
    if not commit["parents"]:
        # Root commit: diff against empty tree
        output = _run_git(repo_path, "diff", "4b825dc642cb6eb9a060e54bf899d15f76ed2e58", sha)
    else:
        output = _run_git(repo_path, "diff", f"{sha}^..{sha}")
    return output


def get_refs(repo_path):
    """Get all branches and tags."""
    fmt = "%(refname)%00%(objectname:short)%00%(creatordate:short)"
    output = _run_git(repo_path, "for-each-ref", f"--format={fmt}", "refs/heads/", "refs/tags/")
    if output is None:
        return {"branches": [], "tags": []}
    branches = []
    tags = []
    for line in output.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\x00")
        if len(parts) < 3:
            continue
        ref = parts[0]
        entry = {"name": ref.split("/", 2)[-1], "hash": parts[1], "date": parts[2]}
        if ref.startswith("refs/heads/"):
            branches.append(entry)
        elif ref.startswith("refs/tags/"):
            tags.append(entry)
    return {"branches": branches, "tags": tags}


def get_last_commit_for_entry(repo_path, ref, path):
    """Get the last commit message for a specific path."""
    output = _run_git(repo_path, "log", "-1", "--format=%s", ref, "--", path)
    if output is None:
        return ""
    return output.strip()


def get_entry_size(repo_path, ref, path):
    """Get size of a blob entry in the tree."""
    output = _run_git(repo_path, "cat-file", "-s", f"{ref}:{path}")
    if output is None:
        return 0
    return int(output.strip())


def create_repo(name, description=""):
    """Create a new bare repository."""
    repos_dir = get_repos_dir()
    repo_path = repos_dir / f"{name}.git"
    if repo_path.exists():
        return False, "Repository already exists"
    repos_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "init", "--bare", str(repo_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return False, result.stderr
    if description:
        (repo_path / "description").write_text(description + "\n")
    return True, str(repo_path)


def delete_repo(name):
    """Delete a bare repository."""
    import shutil
    repo_path = get_repo_path(name)
    if repo_path is None:
        return False, "Repository not found"
    shutil.rmtree(repo_path)
    return True, f"Deleted {repo_path}"
