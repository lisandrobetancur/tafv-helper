"""Imágenes adjuntas por registro (disco + SQLite). No toca el Excel."""
from __future__ import annotations

import sqlite3
import uuid
from contextlib import closing
from datetime import datetime
from pathlib import Path

MAX_BYTES = 10 * 1024 * 1024

# firma del archivo -> (extensión, mime)
def sniff_image(head: bytes) -> tuple[str, str] | None:
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg", "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif", "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp", "image/webp"
    return None


class AttachmentStore:
    def __init__(self, root: Path, db_path: Path):
        self.root = Path(root)
        self.db_path = Path(db_path)
        self.root.mkdir(parents=True, exist_ok=True)
        with closing(self._conn()) as db, db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS attachments (
                    id TEXT PRIMARY KEY,
                    record_id TEXT NOT NULL,
                    stored_name TEXT NOT NULL,
                    original_name TEXT NOT NULL,
                    mime TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    created_at TEXT NOT NULL)"""
            )
            db.execute("CREATE INDEX IF NOT EXISTS ix_att_rec ON attachments(record_id)")

    def _conn(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def _public(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "name": row["original_name"],
            "size": row["size"],
            "created_at": row["created_at"],
            "url": f"/api/attachments/{row['id']}/file",
        }

    def list(self, record_id: str) -> list[dict]:
        with closing(self._conn()) as db:
            rows = db.execute(
                "SELECT * FROM attachments WHERE record_id=? ORDER BY created_at, rowid",
                (record_id,),
            ).fetchall()
        return [self._public(r) for r in rows]

    def counts(self) -> dict[str, int]:
        with closing(self._conn()) as db:
            rows = db.execute(
                "SELECT record_id, COUNT(*) n FROM attachments GROUP BY record_id"
            ).fetchall()
        return {r["record_id"]: r["n"] for r in rows}

    def add(self, record_id: str, original_name: str, data: bytes) -> dict:
        kind = sniff_image(data[:16])
        if kind is None:
            raise ValueError("El archivo no es una imagen válida (JPG, PNG, GIF o WEBP).")
        ext, mime = kind
        aid = uuid.uuid4().hex
        stored = f"{aid}{ext}"
        folder = self.root / record_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / stored).write_bytes(data)
        # Solo el nombre base, sin rutas, para mostrar
        name = Path(original_name.replace("\\", "/")).name[:200] or stored
        with closing(self._conn()) as db, db:
            db.execute(
                "INSERT INTO attachments VALUES (?,?,?,?,?,?,?)",
                (aid, record_id, stored, name, mime, len(data),
                 datetime.now().isoformat(timespec="seconds")),
            )
        return {"id": aid, "name": name, "size": len(data),
                "created_at": "", "url": f"/api/attachments/{aid}/file"}

    def file_info(self, aid: str) -> tuple[Path, str] | None:
        with closing(self._conn()) as db:
            row = db.execute("SELECT * FROM attachments WHERE id=?", (aid,)).fetchone()
        if row is None:
            return None
        return self.root / row["record_id"] / row["stored_name"], row["mime"]

    def delete(self, aid: str) -> bool:
        with closing(self._conn()) as db:
            row = db.execute("SELECT * FROM attachments WHERE id=?", (aid,)).fetchone()
        if row is None:
            return False
        (self.root / row["record_id"] / row["stored_name"]).unlink(missing_ok=True)
        with closing(self._conn()) as db, db:
            db.execute("DELETE FROM attachments WHERE id=?", (aid,))
        return True
