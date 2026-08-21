from contextlib import asynccontextmanager

from fastapi import FastAPI
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
