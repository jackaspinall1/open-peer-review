from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from . import auth, config
from .db import init_db
from .routes import comments, documents


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Open Peer Review", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=config.SECRET_KEY, same_site="lax")
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(comments.router)

# In production this process also serves the built frontend, so the whole app is
# one container with no separate web server and no cross-origin cookie problems.
if (config.STATIC_DIR / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=config.STATIC_DIR / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str, request: Request):
        """Client-side routes (/doc/2, /upload) must return the app shell.

        API and auth paths are registered above, so anything reaching here is
        either a static file or a frontend route.
        """
        if path.startswith(("api/", "auth/")):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = config.STATIC_DIR / path
        if path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(config.STATIC_DIR / "index.html")
