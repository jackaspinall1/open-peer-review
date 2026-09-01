"""Schema changes must reach a database that already exists.

create_all() creates missing tables and never alters existing ones, so a
deployed database quietly keeps the schema it was born with while the code moves
on. That is what "no such column: documents.slug" in production looked like.
"""
import sqlite3

from app import config
from app.db import engine, init_db


def test_missing_columns_and_tables_are_restored_on_startup(client):
    con = sqlite3.connect(config.DB_PATH)
    con.execute("ALTER TABLE documents DROP COLUMN views")
    con.execute("DROP TABLE user_profiles")
    con.execute(
        "INSERT INTO documents (title, pdf_filename, version, slug, created_at)"
        " VALUES ('Older paper', 'x.pdf', 1, NULL, datetime('now'))"
    )
    con.commit()
    assert "views" not in {r[1] for r in con.execute("PRAGMA table_info(documents)")}
    con.close()

    engine.dispose()
    init_db()

    con = sqlite3.connect(config.DB_PATH)
    assert "views" in {r[1] for r in con.execute("PRAGMA table_info(documents)")}
    assert con.execute("SELECT 1 FROM sqlite_master WHERE name='user_profiles'").fetchone()
    title, slug, views = con.execute(
        "SELECT title, slug, views FROM documents WHERE title='Older paper'"
    ).fetchone()
    assert slug and len(slug) == 8      # a paper from before share codes gets one
    assert views == 0                   # and a sensible default rather than null
    con.close()
