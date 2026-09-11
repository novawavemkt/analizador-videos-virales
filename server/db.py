"""
Base de datos local en SQLite (un solo archivo, analizador.db, sin servidor
externo). Se crea automaticamente la primera vez que arranca el backend.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analizador.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    url                 TEXT NOT NULL,
    platform            TEXT,
    autor               TEXT,
    status              TEXT NOT NULL DEFAULT 'pending',
    error_message       TEXT,
    duration_seconds    REAL,
    view_count          INTEGER,
    like_count          INTEGER,
    hook                TEXT,
    formato             TEXT,
    nicho               TEXT,
    awareness_overall   TEXT,
    funciona_porque     TEXT,
    aprendizaje_clave   TEXT,
    transcript          TEXT,
    notas_manuales      TEXT,
    informe_markdown    TEXT,
    puntuacion_media    REAL,
    filtro_angulo_pasa  INTEGER,
    filtro_avatar_pasa  INTEGER,
    filtro_explicacion  TEXT,
    potencial_viral     REAL,
    linked_video_id     INTEGER REFERENCES videos(id) ON DELETE SET NULL,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS client_profiles (
    autor           TEXT PRIMARY KEY,
    angulo          TEXT,
    avatar          TEXT,
    posicionamiento TEXT,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS video_segments (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id         INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    start_seconds    REAL NOT NULL,
    end_seconds      REAL NOT NULL,
    text             TEXT,
    awareness_stage  TEXT NOT NULL,
    ord              INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS video_frames (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id          INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    timestamp_seconds REAL NOT NULL,
    image_bytes       BLOB NOT NULL,
    content_type      TEXT NOT NULL DEFAULT 'image/jpeg'
);

CREATE TABLE IF NOT EXISTS video_comments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id    INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    author      TEXT,
    text        TEXT NOT NULL,
    like_count  INTEGER,
    ord         INTEGER NOT NULL
);
"""


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _migrate(conn):
    """Anade columnas nuevas a bases de datos ya existentes (creadas con un
    esquema anterior), sin romper instalaciones ya en marcha."""
    existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(videos)")}
    if "autor" not in existing_cols:
        conn.execute("ALTER TABLE videos ADD COLUMN autor TEXT")
    if "notas_manuales" not in existing_cols:
        conn.execute("ALTER TABLE videos ADD COLUMN notas_manuales TEXT")
    if "informe_markdown" not in existing_cols:
        conn.execute("ALTER TABLE videos ADD COLUMN informe_markdown TEXT")
    if "puntuacion_media" not in existing_cols:
        conn.execute("ALTER TABLE videos ADD COLUMN puntuacion_media REAL")
    if "filtro_angulo_pasa" not in existing_cols:
        conn.execute("ALTER TABLE videos ADD COLUMN filtro_angulo_pasa INTEGER")
    if "filtro_avatar_pasa" not in existing_cols:
        conn.execute("ALTER TABLE videos ADD COLUMN filtro_avatar_pasa INTEGER")
    if "filtro_explicacion" not in existing_cols:
        conn.execute("ALTER TABLE videos ADD COLUMN filtro_explicacion TEXT")
    if "potencial_viral" not in existing_cols:
        conn.execute("ALTER TABLE videos ADD COLUMN potencial_viral REAL")
    if "linked_video_id" not in existing_cols:
        conn.execute("ALTER TABLE videos ADD COLUMN linked_video_id INTEGER REFERENCES videos(id) ON DELETE SET NULL")


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.commit()
    conn.close()
