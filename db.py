import sqlite3
from pathlib import Path
from datetime import datetime, timezone
import re

DB_PATH = Path(__file__).parent / "memos.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS categories (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS memos (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            title         TEXT NOT NULL DEFAULT '',
            content       TEXT NOT NULL DEFAULT '',
            content_plain TEXT NOT NULL DEFAULT '',
            category_id   INTEGER DEFAULT NULL,
            tags          TEXT NOT NULL DEFAULT '',
            is_pinned     INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT NOT NULL,
            updated_at    TEXT NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS images (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            memo_id       INTEGER NOT NULL,
            filename      TEXT NOT NULL,
            original_name TEXT NOT NULL,
            created_at    TEXT NOT NULL,
            FOREIGN KEY (memo_id) REFERENCES memos(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)
    # Migration: add new columns to existing memos table if missing
    _migrate(conn)
    # Create indexes (after migration ensures columns exist)
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_memos_created ON memos(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_memos_pinned ON memos(is_pinned DESC);
        CREATE INDEX IF NOT EXISTS idx_memos_category ON memos(category_id);
        CREATE INDEX IF NOT EXISTS idx_images_memo ON images(memo_id);
    """)
    # Insert default settings if not exist
    defaults = {
        "hotkey_toggle": "ctrl+shift+m",
        "hotkey_quit": "ctrl+shift+q",
    }
    for k, v in defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (k, v),
        )
    conn.commit()
    conn.close()


def _migrate(conn):
    """Add new columns to existing tables if they don't exist."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(memos)").fetchall()}
    if "category_id" not in existing:
        conn.execute("ALTER TABLE memos ADD COLUMN category_id INTEGER DEFAULT NULL")
    if "tags" not in existing:
        conn.execute("ALTER TABLE memos ADD COLUMN tags TEXT NOT NULL DEFAULT ''")
    conn.commit()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def strip_html(html: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# ── Categories ──────────────────────────────────────────────

def get_categories() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_category(name: str) -> dict:
    conn = get_connection()
    ts = now_iso()
    cur = conn.execute("INSERT INTO categories (name, created_at) VALUES (?, ?)", (name, ts))
    cat_id = cur.lastrowid
    conn.commit()
    row = conn.execute("SELECT * FROM categories WHERE id = ?", (cat_id,)).fetchone()
    conn.close()
    return dict(row)


def update_category(cat_id: int, name: str) -> dict | None:
    conn = get_connection()
    existing = conn.execute("SELECT * FROM categories WHERE id = ?", (cat_id,)).fetchone()
    if not existing:
        conn.close()
        return None
    conn.execute("UPDATE categories SET name = ? WHERE id = ?", (name, cat_id))
    conn.commit()
    row = conn.execute("SELECT * FROM categories WHERE id = ?", (cat_id,)).fetchone()
    conn.close()
    return dict(row)


def delete_category(cat_id: int) -> bool:
    conn = get_connection()
    conn.execute("UPDATE memos SET category_id = NULL WHERE category_id = ?", (cat_id,))
    conn.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()
    return True


# ── Settings ────────────────────────────────────────────────

def get_settings() -> dict:
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def get_setting(key: str, default: str = "") -> str:
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


# ── Memos ───────────────────────────────────────────────────

def create_memo(title: str, content: str, is_pinned: int = 0,
                category_id: int | None = None, tags: str = "") -> dict:
    conn = get_connection()
    ts = now_iso()
    content_plain = strip_html(content)
    cur = conn.execute(
        "INSERT INTO memos (title, content, content_plain, is_pinned, category_id, tags, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (title, content, content_plain, is_pinned, category_id, tags, ts, ts),
    )
    memo_id = cur.lastrowid
    filenames = re.findall(r'/uploads/([^\s"\'>]+)', content)
    for fn in filenames:
        conn.execute(
            "UPDATE images SET memo_id = ? WHERE memo_id = 0 AND filename = ?",
            (memo_id, fn),
        )
    conn.commit()
    memo = conn.execute("SELECT * FROM memos WHERE id = ?", (memo_id,)).fetchone()
    conn.close()
    return dict(memo)


def get_memos(q: str = "", sort: str = "newest", limit: int = 20, offset: int = 0,
              category_id: int | None = None, tag: str = "") -> list:
    conn = get_connection()
    order = "ASC" if sort == "oldest" else "DESC"
    conditions = []
    params = []
    if q:
        conditions.append("(m.title LIKE ? OR m.content_plain LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like])
    if category_id is not None:
        conditions.append("m.category_id = ?")
        params.append(category_id)
    if tag:
        conditions.append("m.tags LIKE ?")
        params.append(f"%{tag}%")
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params.extend([limit, offset])
    rows = conn.execute(
        f"SELECT m.*, c.name as category_name FROM memos m "
        f"LEFT JOIN categories c ON m.category_id = c.id "
        f"{where} ORDER BY m.is_pinned DESC, m.created_at {order} LIMIT ? OFFSET ?",
        params,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_memo(memo_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT m.*, c.name as category_name FROM memos m "
        "LEFT JOIN categories c ON m.category_id = c.id WHERE m.id = ?",
        (memo_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_memo(memo_id: int, title: str, content: str, is_pinned: int,
                category_id: int | None = None, tags: str = "") -> dict | None:
    conn = get_connection()
    existing = conn.execute("SELECT * FROM memos WHERE id = ?", (memo_id,)).fetchone()
    if not existing:
        conn.close()
        return None
    ts = now_iso()
    content_plain = strip_html(content)
    conn.execute(
        "UPDATE memos SET title=?, content=?, content_plain=?, is_pinned=?, "
        "category_id=?, tags=?, updated_at=? WHERE id=?",
        (title, content, content_plain, is_pinned, category_id, tags, ts, memo_id),
    )
    filenames = re.findall(r'/uploads/([^\s"\'>]+)', content)
    for fn in filenames:
        conn.execute(
            "UPDATE images SET memo_id = ? WHERE memo_id = 0 AND filename = ?",
            (memo_id, fn),
        )
    conn.commit()
    memo = conn.execute("SELECT * FROM memos WHERE id = ?", (memo_id,)).fetchone()
    conn.close()
    return dict(memo)


def delete_memo(memo_id: int) -> bool:
    conn = get_connection()
    images = conn.execute("SELECT filename FROM images WHERE memo_id = ?", (memo_id,)).fetchall()
    conn.execute("DELETE FROM memos WHERE id = ?", (memo_id,))
    conn.commit()
    conn.close()
    uploads_dir = Path(__file__).parent / "uploads"
    for img in images:
        p = uploads_dir / img["filename"]
        if p.exists():
            p.unlink()
    return True


# ── Images ──────────────────────────────────────────────────

def create_image(memo_id: int, filename: str, original_name: str) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO images (memo_id, filename, original_name, created_at) VALUES (?, ?, ?, ?)",
        (memo_id, filename, original_name, now_iso()),
    )
    image_id = cur.lastrowid
    conn.commit()
    conn.close()
    return image_id


def delete_image(image_id: int) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT filename FROM images WHERE id = ?", (image_id,)).fetchone()
    if not row:
        conn.close()
        return False
    conn.execute("DELETE FROM images WHERE id = ?", (image_id,))
    conn.commit()
    conn.close()
    p = Path(__file__).parent / "uploads" / row["filename"]
    if p.exists():
        p.unlink()
    return True
