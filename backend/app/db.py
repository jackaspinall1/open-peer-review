from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

import logging

from . import config


log = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine = create_engine(
    f"sqlite:///{config.DB_PATH}",
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")   # or none of the cascades fire
    cursor.execute("PRAGMA journal_mode=WAL")  # readers do not block the writer
    cursor.execute("PRAGMA busy_timeout=5000") # wait rather than fail on a lock
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_columns() -> None:
    """Add any columns the models have and the database does not.

    create_all() creates missing tables but never alters existing ones, so a
    deployed database silently keeps the schema it was born with while the code
    moves on. That is what "no such column" in production looks like. This
    covers the additive case, which is the only kind of change made here; a
    rename or a type change would still need doing by hand.
    """
    from sqlalchemy import text

    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            existing = {
                row[1] for row in conn.execute(text(f"PRAGMA table_info('{table.name}')"))
            }
            if not existing:
                continue                     # create_all will have made it
            for column in table.columns:
                if column.name in existing:
                    continue
                ddl = column.type.compile(engine.dialect)
                if not column.nullable:
                    default = getattr(column.default, "arg", None)
                    literal = "0" if default is None else repr(default).replace("'", "'")
                    ddl += f" NOT NULL DEFAULT {literal}"
                conn.execute(
                    text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {ddl}')
                )
                log.warning("added missing column %s.%s", table.name, column.name)
            for index in table.indexes:
                cols = ", ".join(f'"{c.name}"' for c in index.columns)
                unique = "UNIQUE " if index.unique else ""
                conn.execute(
                    text(f'CREATE {unique}INDEX IF NOT EXISTS "{index.name}" '
                         f'ON "{table.name}" ({cols})')
                )


def _backfill_slugs() -> None:
    """Papers added before share codes existed still need one."""
    from sqlalchemy import text

    from .metadata import new_slug

    with engine.begin() as conn:
        ids = [r[0] for r in conn.execute(text("SELECT id FROM documents WHERE slug IS NULL"))]
        for doc_id in ids:
            taken = lambda c: conn.execute(
                text("SELECT 1 FROM documents WHERE slug = :s"), {"s": c}
            ).first() is not None
            conn.execute(
                text("UPDATE documents SET slug = :s WHERE id = :i"),
                {"s": new_slug(taken), "i": doc_id},
            )


def init_db() -> None:
    from . import models  # noqa: F401  (register tables)
    config.ensure_dirs()
    Base.metadata.create_all(engine)
    _ensure_columns()
    _backfill_slugs()
