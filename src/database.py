"""Neon connection configuration and read-only SQLite import."""

from datetime import datetime
from pathlib import Path
import sqlite3

from sqlalchemy import select, text
from sqlalchemy.engine import make_url

from src.models.user import User, db
from src.models.note import Note, NoteImage


def neon_database_url(value):
    if not value or not value.strip():
        raise ValueError("Configure DATABASE_URL in .env with your Neon PostgreSQL connection string.")
    try:
        url = make_url(value.strip())
    except Exception:
        raise ValueError("DATABASE_URL must be a PostgreSQL connection string.") from None
    if url.drivername not in ('postgres', 'postgresql', 'postgresql+psycopg'):
        raise ValueError("DATABASE_URL must use PostgreSQL, not SQLite.")
    if not url.host or not url.database or not url.username:
        raise ValueError("DATABASE_URL requires a host, database, and username.")
    url = url.set(drivername='postgresql+psycopg')
    if url.query.get('sslmode') not in ('require', 'verify-ca', 'verify-full'):
        url = url.update_query_dict({'sslmode': 'require'})
    return url.render_as_string(hide_password=False)


def import_sqlite(source_path):
    """Import into empty initialized tables atomically without modifying the source."""
    path = Path(source_path).resolve()
    if not path.is_file():
        raise ValueError("SQLite source file does not exist.")
    connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        if 'note' not in tables:
            raise ValueError("The source database has no note table.")
        notes = list(connection.execute('SELECT * FROM note'))
        users = list(connection.execute('SELECT * FROM user')) if 'user' in tables else []
    finally:
        connection.close()

    try:
        if db.engine.dialect.name == 'postgresql':
            # Prevent another writer from creating rows while importing fixed IDs.
            db.session.execute(text('LOCK TABLE "user", note, note_image IN EXCLUSIVE MODE'))
        for model in (User, Note, NoteImage):
            if db.session.execute(select(model.id).limit(1)).first():
                raise ValueError("Migration requires an empty target database; nothing was imported.")
        for row in users:
            db.session.add(User(id=row['id'], username=row['username'], email=row['email']))
        for row in notes:
            db.session.add(Note(
                id=row['id'], title=row['title'], content=row['content'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
            ))
        db.session.flush()
        if db.engine.dialect.name == 'postgresql':
            for table in ('user', 'note'):
                db.session.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('\"{table}\"', 'id'), "
                    f'COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM "{table}"'
                ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return len(notes), len(users)
