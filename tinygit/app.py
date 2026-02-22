import mimetypes
import re
from flask import Flask, render_template, abort, Response, request

from tinygit import config
from tinygit import git_utils

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY


@app.context_processor
def inject_globals():
    return {
        "site_name": config.SITE_NAME,
        "site_tagline": config.SITE_TAGLINE,
        "clone_url_base": config.CLONE_URL_BASE,
        "owner_name": config.OWNER_NAME,
        "owner_email": config.OWNER_EMAIL,
    }


# --- Web Routes ---

@app.route("/")
def index():
    repos = git_utils.list_repos()
    return render_template("index.html", repos=repos)


@app.route("/<repo_name>/")
def repo_summary(repo_name):
    repo_path = git_utils.get_repo_path(repo_name)
    if repo_path is None:
        abort(404)
    branch = git_utils.get_default_branch(repo_path)
    return _render_tree(repo_name, repo_path, branch, "")


@app.route("/<repo_name>/tree/<ref>/")
@app.route("/<repo_name>/tree/<ref>/<path:subpath>")
def tree_view(repo_name, ref, subpath=""):
    repo_path = git_utils.get_repo_path(repo_name)
    if repo_path is None:
        abort(404)
    return _render_tree(repo_name, repo_path, ref, subpath)


def _render_tree(repo_name, repo_path, ref, subpath):
    entries = git_utils.ls_tree(repo_path, ref, subpath)
    if entries is None:
        abort(404)

    # Enrich entries with size and last commit
    for entry in entries:
        entry_path = f"{subpath}/{entry['name']}" if subpath else entry["name"]
        if entry["type"] == "blob":
            size = git_utils.get_entry_size(repo_path, ref, entry_path)
            entry["size"] = git_utils.format_size(size)
        else:
            entry["size"] = "-"
        entry["last_commit"] = git_utils.get_last_commit_for_entry(repo_path, ref, entry_path)
        entry["path"] = entry_path

    # Check for README
    readme_content = None
    readme_name = None
    for name in ["README.md", "README", "README.txt"]:
        check_path = f"{subpath}/{name}" if subpath else name
        for entry in entries:
            if entry["name"] == name:
                data = git_utils.get_blob(repo_path, ref, check_path)
                if data and not git_utils.is_binary(data):
                    readme_content = data.decode("utf-8", errors="replace")
                    readme_name = name
                break
        if readme_content:
            break

    # Render markdown if .md
    readme_html = None
    if readme_content and readme_name and readme_name.endswith(".md"):
        import mistune
        readme_html = mistune.html(readme_content)
        readme_html = re.sub(r'<img[^>]*>', '', readme_html)
    elif readme_content:
        readme_html = f"<pre>{_escape_html(readme_content)}</pre>"

    branch = git_utils.get_default_branch(repo_path)

    # Build breadcrumb parts
    breadcrumb = []
    if subpath:
        parts = subpath.split("/")
        for i, part in enumerate(parts):
            breadcrumb.append({
                "name": part,
                "path": "/".join(parts[:i + 1]),
            })

    return render_template(
        "repo.html",
        repo_name=repo_name,
        ref=ref,
        branch=branch,
        subpath=subpath,
        entries=entries,
        readme_html=readme_html,
        readme_name=readme_name,
        breadcrumb=breadcrumb,
    )


@app.route("/<repo_name>/blob/<ref>/<path:filepath>")
def blob_view(repo_name, ref, filepath):
    repo_path = git_utils.get_repo_path(repo_name)
    if repo_path is None:
        abort(404)

    data = git_utils.get_blob(repo_path, ref, filepath)
    if data is None:
        abort(404)

    size = len(data)
    size_str = git_utils.format_size(size)
    branch = git_utils.get_default_branch(repo_path)
    filename = filepath.split("/")[-1]

    if git_utils.is_binary(data):
        return render_template(
            "blob.html",
            repo_name=repo_name,
            ref=ref,
            filepath=filepath,
            filename=filename,
            branch=branch,
            size=size_str,
            binary=True,
            content=None,
            highlighted=False,
        )

    text = data.decode("utf-8", errors="replace")

    highlighted = False
    content = None
    if config.SYNTAX_HIGHLIGHT:
        try:
            from pygments import highlight
            from pygments.lexers import get_lexer_for_filename, TextLexer
            from pygments.formatters import HtmlFormatter
            from pygments.styles import get_style_by_name
            try:
                lexer = get_lexer_for_filename(filename, stripall=True)
            except Exception:
                lexer = TextLexer()
            style = get_style_by_name(config.PYGMENTS_STYLE)
            formatter = HtmlFormatter(
                linenos="table", cssclass="highlight", style=style,
                nowrap=False,
            )
            content = highlight(text, lexer, formatter)
            highlighted = True
        except Exception:
            pass

    if not highlighted:
        lines = text.split("\n")
        numbered = []
        for i, line in enumerate(lines, 1):
            numbered.append(f"<span class=\"ln\">{i:4d}</span> | {_escape_html(line)}")
        content = "\n".join(numbered)

    return render_template(
        "blob.html",
        repo_name=repo_name,
        ref=ref,
        filepath=filepath,
        filename=filename,
        branch=branch,
        size=size_str,
        binary=False,
        content=content,
        highlighted=highlighted,
    )


@app.route("/<repo_name>/raw/<ref>/<path:filepath>")
def raw_view(repo_name, ref, filepath):
    repo_path = git_utils.get_repo_path(repo_name)
    if repo_path is None:
        abort(404)
    data = git_utils.get_blob(repo_path, ref, filepath)
    if data is None:
        abort(404)
    mime, _ = mimetypes.guess_type(filepath)
    if mime is None:
        mime = "application/octet-stream"
    return Response(data, mimetype=mime)


@app.route("/<repo_name>/log/")
@app.route("/<repo_name>/log/<ref>")
def log_view(repo_name, ref=None):
    repo_path = git_utils.get_repo_path(repo_name)
    if repo_path is None:
        abort(404)
    if ref is None:
        ref = git_utils.get_default_branch(repo_path)

    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1
    skip = (page - 1) * config.COMMITS_PER_PAGE
    commits = git_utils.get_log(repo_path, ref, skip, config.COMMITS_PER_PAGE)
    total = git_utils.get_commit_count(repo_path, ref)
    total_pages = max(1, (total + config.COMMITS_PER_PAGE - 1) // config.COMMITS_PER_PAGE)

    return render_template(
        "log.html",
        repo_name=repo_name,
        ref=ref,
        commits=commits,
        page=page,
        total_pages=total_pages,
    )


@app.route("/<repo_name>/commit/<sha>")
def commit_view(repo_name, sha):
    repo_path = git_utils.get_repo_path(repo_name)
    if repo_path is None:
        abort(404)
    commit = git_utils.get_commit(repo_path, sha)
    if commit is None:
        abort(404)
    diff = git_utils.get_diff(repo_path, sha)

    diff_html = None
    if diff:
        diff_html = _colorize_diff(diff)

    return render_template(
        "commit.html",
        repo_name=repo_name,
        commit=commit,
        diff_html=diff_html,
    )


@app.route("/<repo_name>/refs/")
def refs_view(repo_name):
    repo_path = git_utils.get_repo_path(repo_name)
    if repo_path is None:
        abort(404)
    refs = git_utils.get_refs(repo_path)
    branch = git_utils.get_default_branch(repo_path)
    return render_template(
        "refs.html",
        repo_name=repo_name,
        refs=refs,
        branch=branch,
    )


def _escape_html(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _colorize_diff(diff_text):
    lines = diff_text.split("\n")
    out = []
    for line in lines:
        escaped = _escape_html(line)
        if line.startswith("+++ ") or line.startswith("--- "):
            out.append(f'<span class="diff-meta">{escaped}</span>')
        elif line.startswith("+"):
            out.append(f'<span class="diff-add">{escaped}</span>')
        elif line.startswith("-"):
            out.append(f'<span class="diff-del">{escaped}</span>')
        elif line.startswith("@@"):
            out.append(f'<span class="diff-hunk">{escaped}</span>')
        elif line.startswith("diff "):
            out.append(f'<span class="diff-meta">{escaped}</span>')
        else:
            out.append(escaped)
    return "\n".join(out)

