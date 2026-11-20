from sqlalchemy import inspect, text

from .database import Base, engine

USER_COLUMNS = {
    "name": "VARCHAR(160) DEFAULT ''",
    "headline": "VARCHAR(240) DEFAULT ''",
    "photo_url": "VARCHAR(500) DEFAULT ''",
    "linkedin_sub": "VARCHAR(128)",
    "google_sub": "VARCHAR(128)",
    "default_profile_visibility": "VARCHAR(20) DEFAULT 'group'",
    "show_contact_after_call": "BOOLEAN DEFAULT 1",
}


CHAT_COLUMNS = {
    "kind": "VARCHAR(20) DEFAULT 'message'",
    "deleted_at": "DATETIME",
}


def migrate() -> None:
    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
        existing = {col["name"] for col in inspector.get_columns("users")}
        with engine.begin() as conn:
            for name, ddl in USER_COLUMNS.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))
    if "net_chat_messages" in inspector.get_table_names():
        existing = {col["name"] for col in inspector.get_columns("net_chat_messages")}
        with engine.begin() as conn:
            for name, ddl in CHAT_COLUMNS.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE net_chat_messages ADD COLUMN {name} {ddl}"))
    Base.metadata.create_all(bind=engine)
    sql_path = engine.url.database
    _ = sql_path
    migration = (engine.url.database and None)
    from pathlib import Path

    sql_file = Path(__file__).resolve().parent.parent / "migrations" / "001_event_graph.sql"
    if sql_file.exists():
        script = sql_file.read_text()
        with engine.begin() as conn:
            for statement in script.split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(text(stmt))
