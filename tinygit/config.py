import os

REPOS_DIR = os.environ.get("TINYGIT_REPOS_DIR", "/srv/git/repos")
SITE_NAME = os.environ.get("TINYGIT_SITE_NAME", "tinygit")
SITE_TAGLINE = os.environ.get("TINYGIT_SITE_TAGLINE", "")
CLONE_URL_BASE = os.environ.get("TINYGIT_CLONE_URL_BASE", "git@yourserver:repos")
SYNTAX_HIGHLIGHT = os.environ.get("TINYGIT_SYNTAX_HIGHLIGHT", "true").lower() == "true"
PYGMENTS_STYLE = os.environ.get("TINYGIT_PYGMENTS_STYLE", "bw")
COMMITS_PER_PAGE = int(os.environ.get("TINYGIT_COMMITS_PER_PAGE", "30"))
SECRET_KEY = os.environ.get("TINYGIT_SECRET_KEY", "change-me")
OWNER_NAME = os.environ.get("TINYGIT_OWNER_NAME", "")
OWNER_EMAIL = os.environ.get("TINYGIT_OWNER_EMAIL", "")
