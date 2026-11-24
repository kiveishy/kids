"""SQLite storage for daily tasks (sessions) and the items clicked in them.

One task per activity per day. Today's task is the latest session of that
activity started today; resetting a finished task adds a new session for the
same day, so the finished one stays in history.
"""
import sqlite3
from datetime import date, datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "progress.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    activity    TEXT    NOT NULL DEFAULT 'syllables',
    day         TEXT,
    started_at  TEXT    NOT NULL,
    finished_at TEXT,
    total       INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS clicks (
    session_id  INTEGER NOT NULL REFERENCES sessions(id),
    item        TEXT    NOT NULL,
    clicked_at  TEXT    NOT NULL,
    PRIMARY KEY (session_id, item)
);
"""


def now():
    return datetime.now().isoformat(sep=" ", timespec="seconds")


def today():
    return date.today().isoformat()


def connect():
    DB_PATH.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    _migrate(con)
    return con


def _migrate(con):
    """Upgrade databases created by the first version (no activity/day columns)."""
    cols = {r["name"] for r in con.execute("PRAGMA table_info(sessions)")}
    if "activity" not in cols:
        con.execute("ALTER TABLE sessions ADD COLUMN activity TEXT NOT NULL DEFAULT 'syllables'")
    if "day" not in cols:
        con.execute("ALTER TABLE sessions ADD COLUMN day TEXT")
    con.execute("UPDATE sessions SET day = substr(started_at, 1, 10) WHERE day IS NULL")
    con.execute("CREATE INDEX IF NOT EXISTS ix_sessions_day ON sessions(activity, day)")


def _state(con, row):
    clicked = [r["item"] for r in con.execute(
        "SELECT item FROM clicks WHERE session_id = ? ORDER BY clicked_at", (row["id"],))]
    return {
        "id": row["id"],
        "activity": row["activity"],
        "day": row["day"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "total": row["total"],
        "clicked": clicked,
    }


def _latest_today(con, activity):
    return con.execute(
        "SELECT * FROM sessions WHERE activity = ? AND day = ? ORDER BY id DESC LIMIT 1",
        (activity, today())).fetchone()


def _create(con, activity, total):
    cur = con.execute(
        "INSERT INTO sessions (activity, day, started_at, total) VALUES (?, ?, ?, ?)",
        (activity, today(), now(), total))
    return con.execute("SELECT * FROM sessions WHERE id = ?", (cur.lastrowid,)).fetchone()


def today_task(activity, total):
    """Today's task for the activity; created automatically on first visit of the day."""
    with connect() as con:
        row = _latest_today(con, activity) or _create(con, activity, total)
        return _state(con, row)


def reset_today(activity, total):
    """Start today's task over. Only a finished task is reset; it stays in history."""
    with connect() as con:
        row = _latest_today(con, activity)
        if row is None or row["finished_at"] is not None:
            row = _create(con, activity, total)
        return _state(con, row)


def record_click(session_id, item, valid_items):
    """Store a click; finish the session when every item is done. Returns (state, just_finished)."""
    with connect() as con:
        row = con.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            return None, False
        if row["finished_at"] is None and item in valid_items:
            con.execute("INSERT OR IGNORE INTO clicks VALUES (?, ?, ?)", (session_id, item, now()))
            done = con.execute("SELECT COUNT(*) FROM clicks WHERE session_id = ?",
                               (session_id,)).fetchone()[0]
            if done >= row["total"]:
                con.execute("UPDATE sessions SET finished_at = ? WHERE id = ?", (now(), session_id))
                row = con.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
                return _state(con, row), True
        return _state(con, row), False


def history():
    with connect() as con:
        rows = con.execute("""
            SELECT s.*, COUNT(c.item) AS done, MAX(c.clicked_at) AS last_click,
                   s.id = (SELECT MAX(id) FROM sessions t
                           WHERE t.activity = s.activity AND t.day = s.day) AS is_latest
            FROM sessions s LEFT JOIN clicks c ON c.session_id = s.id
            GROUP BY s.id ORDER BY s.id DESC""").fetchall()
        return [dict(r) for r in rows]
