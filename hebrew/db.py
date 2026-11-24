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
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
-- One row per quiz per day: the best score of the day is kept.
CREATE TABLE IF NOT EXISTS quiz_scores (
    activity    TEXT    NOT NULL,
    day         TEXT    NOT NULL,
    best_score  INTEGER NOT NULL,
    last_score  INTEGER NOT NULL,
    runs        INTEGER NOT NULL,
    questions   INTEGER NOT NULL,
    best_detail TEXT,
    updated_at  TEXT    NOT NULL,
    PRIMARY KEY (activity, day)
);
"""

# Parent-controlled settings and their defaults / allowed range.
SETTINGS = {
    "quiz_questions": {"default": 20, "min": 1, "max": 100},
    "quiz_retries": {"default": 10, "min": 1, "max": 20},
}


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


def get_settings():
    with connect() as con:
        stored = {r["key"]: r["value"] for r in con.execute("SELECT * FROM settings")}
    return {k: int(stored.get(k, spec["default"])) for k, spec in SETTINGS.items()}


def save_settings(values):
    """Store valid settings (clamped to their range). Returns the saved settings."""
    with connect() as con:
        for key, spec in SETTINGS.items():
            if key in values:
                try:
                    v = int(values[key])
                except (TypeError, ValueError):
                    continue
                v = max(spec["min"], min(spec["max"], v))
                con.execute("INSERT INTO settings VALUES (?, ?) "
                            "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, str(v)))
    return get_settings()


def save_quiz_score(activity, score, questions, detail_json):
    """Keep one score row per quiz per day (the best). Returns (best_today, is_new_best)."""
    with connect() as con:
        row = con.execute("SELECT * FROM quiz_scores WHERE activity = ? AND day = ?",
                          (activity, today())).fetchone()
        if row is None:
            con.execute("INSERT INTO quiz_scores VALUES (?, ?, ?, ?, 1, ?, ?, ?)",
                        (activity, today(), score, score, questions, detail_json, now()))
            return score, True
        is_best = score > row["best_score"]
        con.execute("""UPDATE quiz_scores SET last_score = ?, runs = runs + 1, updated_at = ?,
                       best_score = MAX(best_score, ?),
                       questions   = CASE WHEN ? THEN ? ELSE questions END,
                       best_detail = CASE WHEN ? THEN ? ELSE best_detail END
                       WHERE activity = ? AND day = ?""",
                    (score, now(), score, is_best, questions, is_best, detail_json, activity, today()))
        return max(score, row["best_score"]), is_best


def quiz_best_today(activity):
    with connect() as con:
        row = con.execute("SELECT best_score, runs FROM quiz_scores WHERE activity = ? AND day = ?",
                          (activity, today())).fetchone()
        return dict(row) if row else None


def quiz_history():
    with connect() as con:
        return [dict(r) for r in con.execute(
            "SELECT * FROM quiz_scores ORDER BY day DESC, activity")]


def history():
    with connect() as con:
        rows = con.execute("""
            SELECT s.*, COUNT(c.item) AS done, MAX(c.clicked_at) AS last_click,
                   s.id = (SELECT MAX(id) FROM sessions t
                           WHERE t.activity = s.activity AND t.day = s.day) AS is_latest
            FROM sessions s LEFT JOIN clicks c ON c.session_id = s.id
            GROUP BY s.id ORDER BY s.id DESC""").fetchall()
        return [dict(r) for r in rows]
