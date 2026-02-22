#!/usr/bin/env python3
import sys
import click

from tinygit import config
from tinygit import git_utils
from tinygit.remote import get_remote, get_repos_dir, load_config, save_config, ssh_run


@click.group()
def cli():
    """tinygit — minimal git web interface"""
    pass


# -- remote subcommand group --------------------------------------------------

@cli.group()
def remote():
    """Configure a remote TinyGit server."""
    pass


@remote.command("set")
@click.argument("host")
@click.option("--repos-dir", default="/srv/git/repos", help="Repos directory on remote")
def remote_set(host, repos_dir):
    """Set the remote host (e.g. user@myserver.com)."""
    cfg = load_config()
    cfg["remote"] = host
    cfg["repos_dir"] = repos_dir
    save_config(cfg)
    click.echo(f"remote set to {host}")
    click.echo(f"repos dir: {repos_dir}")


@remote.command("show")
def remote_show():
    """Show current remote config."""
    cfg = load_config()
    host = cfg.get("remote")
    if not host:
        click.echo("no remote configured")
        return
    click.echo(f"remote:    {host}")
    click.echo(f"repos dir: {cfg.get('repos_dir', '/srv/git/repos')}")


@remote.command("remove")
def remote_remove():
    """Clear remote config."""
    cfg = load_config()
    cfg.pop("remote", None)
    cfg.pop("repos_dir", None)
    save_config(cfg)
    click.echo("remote config removed")


# -- setup command -------------------------------------------------------------

@cli.command()
def setup():
    """Set up TinyGit on a remote server via SSH."""
    host = get_remote()
    if not host:
        click.echo("error: no remote configured. Run: tinygit remote set user@host", err=True)
        sys.exit(1)

    repos_dir = get_repos_dir() or "/srv/git/repos"
    click.echo(f"Setting up TinyGit on {host}...")

    commands = [
        f"sudo mkdir -p {repos_dir}",
        f"sudo chown $(whoami) {repos_dir}",
        "pip install tinygit 2>/dev/null || pip install git+https://github.com/davidsenack/tinygit.git",
    ]
    for cmd in commands:
        click.echo(f"  running: {cmd}")
        rc = ssh_run(host, cmd)
        if rc != 0:
            click.echo(f"error: command failed with exit code {rc}", err=True)
            sys.exit(rc)

    click.echo("setup complete")


# -- stop command --------------------------------------------------------------

@cli.command()
def stop():
    """Stop a remote TinyGit server."""
    host = get_remote()
    if not host:
        click.echo("error: no remote configured", err=True)
        sys.exit(1)

    click.echo(f"Stopping tinygit on {host}...")
    rc = ssh_run(host, "pkill -f 'tinygit serve' || true")
    if rc == 0:
        click.echo("stopped")
    else:
        click.echo("error: failed to stop remote server", err=True)
        sys.exit(rc)


# -- existing commands (with remote support) -----------------------------------

@cli.command()
@click.option("--host", "bind_host", default="0.0.0.0", help="Bind address")
@click.option("--port", default=5000, help="Port number")
@click.option("--debug", is_flag=True, help="Enable debug mode")
def serve(bind_host, port, debug):
    """Start the web UI."""
    host = get_remote()
    if host:
        repos_dir = get_repos_dir() or "/srv/git/repos"
        cmd = f"TINYGIT_REPOS_DIR={repos_dir} nohup tinygit serve --port {port} > /dev/null 2>&1 &"
        click.echo(f"Starting tinygit on {host}:{port}...")
        rc = ssh_run(host, cmd)
        if rc == 0:
            click.echo(f"serving at http://{host.split('@')[-1]}:{port}")
        else:
            sys.exit(rc)
        return

    from tinygit.app import app
    app.run(host=bind_host, port=port, debug=debug)


@cli.command()
@click.argument("name")
@click.argument("description", default="")
def create(name, description):
    """Create a new bare repo."""
    host = get_remote()
    if host:
        repos_dir = get_repos_dir() or "/srv/git/repos"
        cmd = f"TINYGIT_REPOS_DIR={repos_dir} tinygit create {name}"
        if description:
            cmd += f" '{description}'"
        rc = ssh_run(host, cmd)
        if rc != 0:
            sys.exit(rc)
        return

    ok, msg = git_utils.create_repo(name, description)
    if ok:
        click.echo(f"created {name}")
        click.echo(f"clone:  {config.CLONE_URL_BASE}/{name}.git")
    else:
        click.echo(f"error: {msg}", err=True)
        sys.exit(1)


@cli.command("list")
def list_repos():
    """List all repos."""
    host = get_remote()
    if host:
        repos_dir = get_repos_dir() or "/srv/git/repos"
        rc = ssh_run(host, f"TINYGIT_REPOS_DIR={repos_dir} tinygit list")
        if rc != 0:
            sys.exit(rc)
        return

    repos = git_utils.list_repos()
    if not repos:
        click.echo("no repos found")
        return
    for repo in repos:
        desc = f"  {repo['description']}" if repo["description"] else ""
        click.echo(f"  {repo['name']:<20}{desc}")


@cli.command()
@click.argument("name")
@click.option("--yes", is_flag=True, help="Skip confirmation")
def delete(name, yes):
    """Delete a repo."""
    host = get_remote()
    if host:
        if not yes:
            click.confirm(f"delete {name}?", abort=True)
        repos_dir = get_repos_dir() or "/srv/git/repos"
        rc = ssh_run(host, f"TINYGIT_REPOS_DIR={repos_dir} tinygit delete {name} --yes")
        if rc != 0:
            sys.exit(rc)
        return

    if not yes:
        click.confirm(f"delete {name}?", abort=True)
    ok, msg = git_utils.delete_repo(name)
    if ok:
        click.echo(f"deleted {name}")
    else:
        click.echo(f"error: {msg}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
