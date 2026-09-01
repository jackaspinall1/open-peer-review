"""Application settings, read from environment variables with dev-friendly defaults.

A backend/.env file (KEY=VALUE lines, # comments) is loaded first; real
environment variables win over .env entries.
"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_env_file = Path(__file__).resolve().parents[1] / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

DATA_DIR = Path(os.environ.get("DATA_DIR", PROJECT_ROOT / "data"))
PDF_DIR = DATA_DIR / "pdfs"
DB_PATH = DATA_DIR / "app.db"

def _secret_key() -> str:
    """Session-signing key.

    A hardcoded default is a real vulnerability once the source is public:
    anyone who reads it can forge a session cookie for any ORCID iD. So there is
    no default. If the environment does not supply one, generate a random key
    and persist it, which keeps sessions stable across restarts without ever
    sharing a known secret.
    """
    from_env = os.environ.get("SECRET_KEY", "").strip()
    if from_env:
        return from_env
    import secrets

    key_file = DATA_DIR / "secret_key"
    if key_file.exists():
        return key_file.read_text().strip()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    key = secrets.token_urlsafe(48)
    key_file.write_text(key)
    key_file.chmod(0o600)
    return key


SECRET_KEY = _secret_key()

# ORCID OAuth (https://info.orcid.org/documentation/api-tutorials/)
# Set ORCID_ENV=sandbox to use the sandbox member site.
ORCID_ENV = os.environ.get("ORCID_ENV", "production")
ORCID_BASE = "https://sandbox.orcid.org" if ORCID_ENV == "sandbox" else "https://orcid.org"
ORCID_CLIENT_ID = os.environ.get("ORCID_CLIENT_ID", "")
ORCID_CLIENT_SECRET = os.environ.get("ORCID_CLIENT_SECRET", "")
ORCID_REDIRECT_URI = os.environ.get("ORCID_REDIRECT_URI", "http://localhost:5173/auth/orcid/callback")

# Where to send the browser after login (the Vite dev server in development).
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

# ORCID iDs allowed to remove comments, comma-separated.
ADMIN_ORCIDS = {
    o.strip().upper() for o in os.environ.get("ADMIN_ORCIDS", "").split(",") if o.strip()
}

# OpenAlex asks for a mailto to route you into the polite (faster) request pool.
OPENALEX_MAILTO = os.environ.get("OPENALEX_MAILTO", "")

# Built frontend, served by this app in production. In development the Vite dev
# server serves it instead and proxies /api and /auth here.
STATIC_DIR = Path(os.environ.get("STATIC_DIR", PROJECT_ROOT / "frontend" / "dist"))


def ensure_dirs() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
