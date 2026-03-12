from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sha1 TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    original_relpath TEXT NOT NULL,
    thumb_relpath TEXT NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    mime_type TEXT NOT NULL,
    added_at TEXT NOT NULL,
    embedding_row INTEGER UNIQUE NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_images_embedding_row ON images(embedding_row);
"""


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path) -> None:
    with _connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


def count_images(db_path: Path) -> int:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM images").fetchone()
        return int(row["n"])


def get_image_by_sha1(db_path: Path, sha1: str) -> dict[str, Any] | None:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM images WHERE sha1 = ?", (sha1,)).fetchone()
        return dict(row) if row else None


def insert_image(db_path: Path, record: dict[str, Any]) -> int:
    with _connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO images (
                sha1, filename, original_relpath, thumb_relpath,
                width, height, mime_type, added_at, embedding_row
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["sha1"],
                record["filename"],
                record["original_relpath"],
                record["thumb_relpath"],
                record["width"],
                record["height"],
                record["mime_type"],
                record["added_at"],
                record["embedding_row"],
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_images_by_rows(db_path: Path, rows: list[int]) -> dict[int, dict[str, Any]]:
    if not rows:
        return {}
    placeholders = ",".join("?" for _ in rows)
    with _connect(db_path) as conn:
        result = conn.execute(
            f"SELECT * FROM images WHERE embedding_row IN ({placeholders})",
            tuple(rows),
        ).fetchall()
    return {int(row["embedding_row"]): dict(row) for row in result}


def list_recent_images(db_path: Path, limit: int = 24) -> list[dict[str, Any]]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM images ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
