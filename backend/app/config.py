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

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# "mock" = dev login form only; "orcid" = real ORCID sign-in only (requires a
# registered public API client); "both" = ORCID button plus the dev form.
AUTH_MODE = os.environ.get("AUTH_MODE", "mock")

# ORCID OAuth (https://info.orcid.org/documentation/api-tutorials/)
# Set ORCID_ENV=sandbox to use the sandbox member site.
ORCID_ENV = os.environ.get("ORCID_ENV", "production")
ORCID_BASE = "https://sandbox.orcid.org" if ORCID_ENV == "sandbox" else "https://orcid.org"
ORCID_CLIENT_ID = os.environ.get("ORCID_CLIENT_ID", "")
ORCID_CLIENT_SECRET = os.environ.get("ORCID_CLIENT_SECRET", "")
ORCID_REDIRECT_URI = os.environ.get("ORCID_REDIRECT_URI", "http://localhost:5173/auth/orcid/callback")

# Where to send the browser after login (the Vite dev server in development).
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

# OpenAlex asks for a mailto to route you into the polite (faster) request pool.
OPENALEX_MAILTO = os.environ.get("OPENALEX_MAILTO", "")

def ensure_dirs() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
