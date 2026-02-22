#!/usr/bin/env python3
import sys
import click

from tinygit import config
from tinygit import git_utils


@click.group()
def cli():
    """tinygit — minimal git web interface"""
    pass


@cli.command()
@click.option("--host", default="0.0.0.0", help="Bind address")
@click.option("--port", default=5000, help="Port number")
@click.option("--debug", is_flag=True, help="Enable debug mode")
def serve(host, port, debug):
    """Start the web UI."""
    from tinygit.app import app
    app.run(host=host, port=port, debug=debug)


@cli.command()
@click.argument("name")
@click.argument("description", default="")
def create(name, description):
    """Create a new bare repo."""
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
